from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from trendbot.backtest import run_backtest
from trendbot.binance_archive import point_in_time_eligibility
from trendbot.config import TrendConfig
from trendbot.data import load_csv_panels


WEIGHTS = (0.0, 0.25, 0.50, 0.70, 1.0)
YEARS = range(2020, 2026)


def period_metrics(daily: pd.DataFrame, start: str, end: str) -> dict[str, float | int]:
    frame = daily.loc[start:end]
    returns = frame["net_return"]
    total = float((1 + returns).prod() - 1)
    std = float(returns.std(ddof=1))
    curve = (1 + returns).cumprod()
    drawdown = curve / curve.cummax() - 1
    return {
        "days": int(len(frame)),
        "return": total,
        "sharpe": float(returns.mean() / std * np.sqrt(365)) if std > 0 else 0.0,
        "max_drawdown": float(drawdown.min()) if len(drawdown) else 0.0,
        "turnover": float(frame["turnover"].sum()),
        "cost_drag": float(frame["cost_return"].sum()),
    }


def summarize(result) -> dict:
    yearly = {
        str(year): period_metrics(result.daily, f"{year}-01-01", f"{year}-12-31")
        for year in YEARS
    }
    year_returns = np.array([item["return"] for item in yearly.values()])
    return {
        "full": result.metrics,
        "yearly": yearly,
        "anchored_next_year": {
            # The rule is not refit; labels make the chronological decision
            # boundary explicit and prevent aggregate performance hiding a fold.
            f"history_through_{year - 1}_next_{year}": yearly[str(year)]
            for year in range(2021, 2026)
        },
        "stability": {
            "positive_years": int((year_returns > 0).sum()),
            "negative_years": int((year_returns < 0).sum()),
            "median_year_return": float(np.median(year_returns)),
            "worst_year_return": float(year_returns.min()),
            "year_return_std": float(year_returns.std(ddof=1)),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panels = load_csv_panels(args.data)
    opens, closes, funding = panels["open"], panels["close"], panels["funding"]
    tradeable = point_in_time_eligibility(panels["quote_volume"], closes)

    control_config = TrendConfig()
    print("running frozen short-vol control", flush=True)
    control = summarize(run_backtest(opens, closes, control_config, funding, tradeable))
    variants = {}
    for cost in (10.0, 20.0):
        for weight in WEIGHTS:
            name = f"short_weight_{weight:.2f}_cost_{int(cost)}bps"
            print(f"running {name}", flush=True)
            config = replace(
                control_config,
                vol_forecast="blend",
                vol_blend_short=weight,
                vol_short_min_periods=20,
                vol_long_min_periods=60,
                cost_bps=cost,
            )
            variants[name] = {
                "short_weight": weight,
                "long_weight": 1.0 - weight,
                "cost_bps": cost,
                **summarize(run_backtest(opens, closes, config, funding, tradeable)),
            }

    payload = {
        "status": "structural_grid_not_automatically_promoted",
        "hypothesis": "A slower volatility component may reduce transition oversizing without changing trend direction or selecting tokens.",
        "predeclared_grid": {
            "short_weights": list(WEIGHTS),
            "long_weights": [1 - value for value in WEIGHTS],
            "cost_bps": [10, 20],
        },
        "control": control,
        "variants": variants,
        "interpretation_rule": "Prefer broad fold stability and neighboring-weight agreement. Do not choose a blend solely because it improves 2023 or has the highest aggregate return.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "control": {
            "total": control["full"]["total_return"],
            "sharpe": control["full"]["sharpe"],
            "2023": control["yearly"]["2023"]["return"],
        },
        "variants": {
            name: {
                "total": value["full"]["total_return"],
                "sharpe": value["full"]["sharpe"],
                "drawdown": value["full"]["max_drawdown"],
                "2023": value["yearly"]["2023"]["return"],
                "2024_2025": (1 + value["yearly"]["2024"]["return"])
                * (1 + value["yearly"]["2025"]["return"]) - 1,
            }
            for name, value in variants.items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
