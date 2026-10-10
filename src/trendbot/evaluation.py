from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .backtest import BacktestResult, run_backtest
from .config import TrendConfig


@dataclass(frozen=True)
class ChronologicalSplit:
    design_end: str
    validation_end: str

    def masks(self, index: pd.DatetimeIndex) -> dict[str, pd.Series]:
        design_end = pd.Timestamp(self.design_end, tz="UTC")
        validation_end = pd.Timestamp(self.validation_end, tz="UTC")
        if validation_end <= design_end:
            raise ValueError("validation_end must be after design_end")
        return {
            "design": index <= design_end,
            "validation": (index > design_end) & (index <= validation_end),
            "test": index > validation_end,
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
    masks = split.masks(result.daily.index)
    reports: dict[str, dict[str, float]] = {}
    for label, mask in masks.items():
        frame = result.daily.loc[mask]
        if frame.empty:
            reports[label] = {"bars": 0}
            continue
        period_return = float((1.0 + frame["net_return"]).prod() - 1.0)
        reports[label] = {
            "bars": int(len(frame)),
            "return": period_return,
            "mean_gross_exposure": float(frame["gross_exposure"].mean()),
            "turnover": float(frame["turnover"].sum()),
            "cost_return": float(frame["cost_return"].sum()),
            "funding_return": float(frame["funding_return"].sum()),
        }
    return result, reports

