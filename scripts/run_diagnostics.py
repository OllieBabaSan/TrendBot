from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from trendbot.backtest import run_backtest
from trendbot.binance_archive import point_in_time_eligibility
from trendbot.config import TrendConfig
from trendbot.data import load_csv_panels


def period_return(frame: pd.DataFrame) -> float:
    return float((1.0 + frame["net_return"]).prod() - 1.0) if len(frame) else 0.0


def funding_archive_coverage(
    tradeable: pd.DataFrame, cache: Path
) -> dict[str, float | int]:
    covered = 0
    eligible = 0
    for symbol in tradeable.columns:
        active_dates = tradeable.index[tradeable[symbol].to_numpy(dtype=bool)]
        eligible += len(active_dates)
        known_months = {
            path.stem for path in (cache / "funding" / symbol).glob("*.zip")
        } if (cache / "funding" / symbol).exists() else set()
        covered += sum(date.strftime("%Y-%m") in known_months for date in active_dates)
    return {
        "eligible_symbol_days": eligible,
        "covered_symbol_days": covered,
        "coverage": covered / eligible if eligible else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panels = load_csv_panels(args.data)
    opens, closes, funding = panels["open"], panels["close"], panels["funding"]
    config = TrendConfig()
    thresholds = [1_000_000, 5_000_000, 25_000_000, 100_000_000]
    sensitivity = {}
    baseline_result = None
    baseline_tradeable = None
    for threshold in thresholds:
        tradeable = point_in_time_eligibility(
            panels["quote_volume"],
            closes,
            minimum_median_quote_volume=threshold,
        )
        result = run_backtest(opens, closes, config, funding, tradeable)
        sensitivity[str(threshold)] = {
            "metrics": result.metrics,
            "average_eligible_markets": float(tradeable.sum(axis=1).mean()),
            "maximum_eligible_markets": int(tradeable.sum(axis=1).max()),
        }
        if threshold == 5_000_000:
            baseline_result = result
            baseline_tradeable = tradeable

    assert baseline_result is not None and baseline_tradeable is not None
    daily = baseline_result.daily
    monthly = daily.groupby(daily.index.to_period("M")).apply(
        period_return, include_groups=False
    )
    btc = closes["BTCUSDT"]
    btc_regime = btc.shift(1) > btc.shift(1).rolling(200, min_periods=200).mean()
    bull = daily.loc[btc_regime.reindex(daily.index).fillna(False)]
    bear = daily.loc[~btc_regime.reindex(daily.index).fillna(False)]
    payload = {
        "liquidity_sensitivity": sensitivity,
        "funding_archive": funding_archive_coverage(baseline_tradeable, args.cache),
        "leverage": {
            "maximum_gross_exposure": float(daily["gross_exposure"].max()),
            "days_above_1x": int((daily["gross_exposure"] > 1.0).sum()),
            "days_near_1_5x_cap": int((daily["gross_exposure"] >= 1.49).sum()),
            "average_gross_exposure": float(daily["gross_exposure"].mean()),
        },
        "btc_200d_regime": {
            "above": {"days": int(len(bull)), "return": period_return(bull)},
            "below_or_unavailable": {"days": int(len(bear)), "return": period_return(bear)},
        },
        "monthly": {
            "positive_months": int((monthly > 0).sum()),
            "negative_months": int((monthly < 0).sum()),
            "best": {str(index): float(value) for index, value in monthly.nlargest(10).items()},
            "worst": {str(index): float(value) for index, value in monthly.nsmallest(10).items()},
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
