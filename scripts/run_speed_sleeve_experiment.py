from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from trendbot.backtest import forward_mark_returns, performance_metrics, run_backtest
from trendbot.binance_archive import point_in_time_eligibility
from trendbot.config import TrendConfig
from trendbot.data import load_csv_panels


FOLDS = {
    "2020": ("2020-01-01", "2020-12-31"),
    "2021": ("2021-01-01", "2021-12-31"),
    "2022": ("2022-01-01", "2022-12-31"),
    "2023": ("2023-01-01", "2023-12-31"),
    "2024": ("2024-01-01", "2024-12-31"),
    "2025": ("2025-01-01", "2025-12-31"),
    "design_2020_2022": ("2020-01-01", "2022-12-31"),
    "corroboration_2024_2025": ("2024-01-01", "2025-12-31"),
}


def combine_equal_sleeves(position_frames: list[pd.DataFrame], max_gross: float) -> pd.DataFrame:
    combined = sum(position_frames) / len(position_frames)
    gross = combined.abs().sum(axis=1)
    scale = (max_gross / gross).clip(upper=1.0).fillna(1.0)
    return combined.mul(scale, axis=0)


def evaluate_combined_positions(positions, opens, closes, funding, config):
    positions = positions.reindex(index=opens.index[:-1], columns=opens.columns).fillna(0.0)
    funding = funding.reindex(index=positions.index, columns=positions.columns).fillna(0.0)
    records = []
    previous = np.zeros(len(opens.columns), dtype=float)
    equity = config.initial_equity
    forward_frame, terminal_frame = forward_mark_returns(opens, closes)
    for i, date in enumerate(positions.index):
        held = positions.iloc[i].to_numpy(dtype=float, copy=True)
        turnover = float(np.abs(held - previous).sum())
        terminal = terminal_frame.loc[date].to_numpy(dtype=bool)
        forward = forward_frame.loc[date].to_numpy(dtype=float)
        turnover += float(np.nansum(np.where(terminal, np.abs(held * (1.0 + forward)), 0.0)))
        gross_return = float(np.nansum(held * forward))
        funding_return = float(np.nansum(held * funding.iloc[i].to_numpy(dtype=float)))
        cost_return = turnover * config.cost_bps / 10_000.0
        net_return = gross_return - funding_return - cost_return
        equity *= 1.0 + net_return
        records.append({
            "equity": equity,
            "gross_return": gross_return,
            "funding_return": funding_return,
            "cost_return": cost_return,
            "net_return": net_return,
            "turnover": turnover,
            "gross_exposure": float(np.abs(held).sum()),
            "net_exposure": float(held.sum()),
        })
        equity_factor = 1.0 + net_return
        drifted = held * (1.0 + np.nan_to_num(forward))
        previous = (
            drifted / equity_factor
            if np.isfinite(equity_factor) and equity_factor > 0
            else np.zeros_like(drifted)
        )
        previous = np.where(terminal, 0.0, previous)
    return pd.DataFrame(records, index=positions.index)


def period_statistics(daily: pd.DataFrame, start: str, end: str) -> dict[str, float]:
    frame = daily.loc[start:end]
    returns = frame["net_return"]
    total = float((1.0 + returns).prod() - 1.0)
    std = float(returns.std(ddof=1))
    sharpe = float(returns.mean() / std * np.sqrt(365)) if std > 0 else 0.0
    curve = (1.0 + returns).cumprod()
    drawdown = curve / curve.cummax() - 1.0
    return {
        "days": int(len(frame)),
        "return": total,
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()) if len(drawdown) else 0.0,
        "turnover": float(frame["turnover"].sum()),
        "cost_drag": float(frame["cost_return"].sum()),
        "funding_drag": float(frame["funding_return"].sum()),
        "average_gross_exposure": float(frame["gross_exposure"].mean()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panels = load_csv_panels(args.data)
    opens, closes, funding = panels["open"], panels["close"], panels["funding"]
    tradeable = point_in_time_eligibility(panels["quote_volume"], closes)
    config = TrendConfig()

    baseline = run_backtest(opens, closes, config, funding, tradeable)
    sleeves = []
    sleeve_metrics = {}
    for speed in config.speeds:
        result = run_backtest(opens, closes, replace(config, speeds=(speed,)), funding, tradeable)
        sleeves.append(result.positions)
        sleeve_metrics[f"{speed[0]}_{speed[1]}"] = result.metrics
    combined_positions = combine_equal_sleeves(sleeves, config.max_gross_leverage)
    combined_daily = evaluate_combined_positions(combined_positions, opens, closes, funding, config)

    payload = {
        "status": "research_counterfactual_not_promoted",
        "construction": "Equal one-third capital weights across independently risk-sized 16/48, 32/96, and 64/192 sleeves; net positions; shared 1.5x hard gross cap; costs charged on combined turnover.",
        "baseline": {
            "full": baseline.metrics,
            "folds": {name: period_statistics(baseline.daily, start, end) for name, (start, end) in FOLDS.items()},
        },
        "speed_sleeve_ensemble": {
            "full": performance_metrics(combined_daily, config),
            "folds": {name: period_statistics(combined_daily, start, end) for name, (start, end) in FOLDS.items()},
            "maximum_gross_exposure": float(combined_daily["gross_exposure"].max()),
        },
        "individual_sleeves": sleeve_metrics,
        "evaluation_note": "All calendar folds are reported. 2024-2025 has already been inspected and is corroborating, not pristine holdout evidence.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "baseline": {k: v["return"] for k, v in payload["baseline"]["folds"].items()},
        "sleeves": {k: v["return"] for k, v in payload["speed_sleeve_ensemble"]["folds"].items()},
        "sleeve_full": payload["speed_sleeve_ensemble"]["full"],
    }, indent=2))


if __name__ == "__main__":
    main()
