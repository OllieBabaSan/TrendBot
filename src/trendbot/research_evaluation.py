from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np
import pandas as pd

from .backtest import BacktestResult, run_backtest
from .config import TrendConfig


@dataclass(frozen=True)
class ChronologicalSplit:
    """Compatibility split for quick design/validation/test diagnostics."""

    design_end: str
    validation_end: str

    def masks(self, index: pd.DatetimeIndex) -> dict[str, np.ndarray]:
        design_end = pd.Timestamp(self.design_end, tz="UTC")
        validation_end = pd.Timestamp(self.validation_end, tz="UTC")
        if validation_end <= design_end:
            raise ValueError("validation_end must be after design_end")
        return {
            "design": index <= design_end,
            "validation": (index > design_end) & (index <= validation_end),
            "test": index > validation_end,
        }


@dataclass(frozen=True)
class ChronologicalPartitions:
    """Four-stage contract that protects a genuinely final test period."""

    design_end: str
    validation_end: str
    confirmation_end: str
    test_end: str | None = None

    def validate(self, index: pd.DatetimeIndex) -> None:
        boundaries = pd.to_datetime(
            [self.design_end, self.validation_end, self.confirmation_end], utc=True
        )
        if not boundaries.is_monotonic_increasing or boundaries.has_duplicates:
            raise ValueError("partition boundaries must be strictly increasing")
        if boundaries[0] <= index.min() or boundaries[-1] >= index.max():
            raise ValueError("partitions must leave observations on both sides")
        if self.test_end is not None:
            test_end = pd.Timestamp(self.test_end, tz="UTC")
            if test_end <= boundaries[-1] or test_end > index.max():
                raise ValueError("test_end must follow confirmation and exist in data")

    def masks(self, index: pd.DatetimeIndex) -> dict[str, np.ndarray]:
        self.validate(index)
        design = pd.Timestamp(self.design_end, tz="UTC")
        validation = pd.Timestamp(self.validation_end, tz="UTC")
        confirmation = pd.Timestamp(self.confirmation_end, tz="UTC")
        test = pd.Timestamp(self.test_end, tz="UTC") if self.test_end else index.max()
        return {
            "design": index <= design,
            "validation": (index > design) & (index <= validation),
            "confirmation": (index > validation) & (index <= confirmation),
            "final_test": (index > confirmation) & (index <= test),
        }

    def to_dict(self) -> dict:
        return asdict(self)


def metrics_for_returns(returns: pd.Series, annualization: int = 365) -> dict[str, float]:
    values = returns.dropna().astype(float)
    if values.empty:
        return {"observations": 0.0}
    equity = (1.0 + values).cumprod()
    years = max(len(values) / annualization, 1 / annualization)
    total = float(equity.iloc[-1] - 1.0)
    std = float(values.std(ddof=1))
    downside = float(values[values < 0].std(ddof=1))
    curve = pd.concat([pd.Series([1.0]), equity.reset_index(drop=True)])
    drawdown = curve / curve.cummax() - 1.0
    max_drawdown = float(drawdown.min())
    cagr = float((1 + total) ** (1 / years) - 1) if total > -1 else -1.0
    return {
        "observations": float(len(values)),
        "total_return": total,
        "cagr": cagr,
        "sharpe": float(values.mean() / std * np.sqrt(annualization)) if std > 0 else 0.0,
        "sortino": (
            float(values.mean() / downside * np.sqrt(annualization))
            if downside > 0
            else 0.0
        ),
        "max_drawdown": max_drawdown,
        "calmar": float(cagr / abs(max_drawdown)) if max_drawdown < 0 else 0.0,
        "positive_period_fraction": float((values > 0).mean()),
    }


def evaluate_splits(
    opens: pd.DataFrame,
    closes: pd.DataFrame,
    config: TrendConfig,
    split: ChronologicalSplit,
    funding: pd.DataFrame | None = None,
    tradeable: pd.DataFrame | None = None,
) -> tuple[BacktestResult, dict[str, dict[str, float]]]:
    """Run once, then report disjoint periods without resetting positions."""
    result = run_backtest(opens, closes, config, funding, tradeable)
    reports: dict[str, dict[str, float]] = {}
    for label, mask in split.masks(result.daily.index).items():
        frame = result.daily.loc[mask]
        if frame.empty:
            reports[label] = {"bars": 0}
            continue
        reports[label] = {
            "bars": int(len(frame)),
            **metrics_for_returns(frame["net_return"], config.annualization_days),
            "mean_gross_exposure": float(frame["gross_exposure"].mean()),
            "turnover": float(frame["turnover"].sum()),
            "cost_return": float(frame["cost_return"].sum()),
            "funding_return": float(frame["funding_return"].sum()),
        }
    return result, reports


def partition_report(
    result: BacktestResult,
    partitions: ChronologicalPartitions,
    annualization: int = 365,
) -> dict[str, dict[str, float]]:
    return {
        name: metrics_for_returns(result.daily.loc[mask, "net_return"], annualization)
        for name, mask in partitions.masks(result.daily.index).items()
    }


def contribution_report(positions: pd.DataFrame, opens: pd.DataFrame) -> dict[str, object]:
    aligned = opens.reindex(index=positions.index.union(opens.index)).sort_index()
    forward = aligned.shift(-1) / aligned - 1.0
    gross = positions * forward.reindex(positions.index)
    by_market = gross.sum().sort_values(ascending=False)
    positive_total = float(by_market.clip(lower=0).sum())
    top_share = (
        float(by_market.iloc[0] / positive_total)
        if len(by_market) and positive_total > 0 and by_market.iloc[0] > 0
        else 0.0
    )
    by_month = gross.sum(axis=1).groupby(gross.index.to_period("M")).sum()
    positive_months = float(by_month.clip(lower=0).sum())
    top_month_share = (
        float(by_month.max() / positive_months)
        if len(by_month) and positive_months > 0 and by_month.max() > 0
        else 0.0
    )
    return {
        "market_contribution": {str(k): float(v) for k, v in by_market.items()},
        "top_positive_market_share": top_share,
        "top_positive_month_share": top_month_share,
        "positive_markets": int((by_market > 0).sum()),
        "negative_markets": int((by_market < 0).sum()),
        "median_market_contribution": float(by_market.median()) if len(by_market) else 0.0,
    }


def stress_costs(
    opens: pd.DataFrame,
    closes: pd.DataFrame,
    base: TrendConfig,
    costs_bps: tuple[float, ...] = (5.0, 10.0, 20.0),
    funding: pd.DataFrame | None = None,
    tradeable: pd.DataFrame | None = None,
    runner: Callable[..., BacktestResult] = run_backtest,
) -> dict[str, dict[str, float]]:
    reports: dict[str, dict[str, float]] = {}
    for cost in costs_bps:
        config = TrendConfig(**{**base.to_dict(), "cost_bps": cost})
        reports[f"{cost:g}bps"] = runner(
            opens, closes, config, funding, tradeable
        ).metrics
    return reports

