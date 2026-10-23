from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.run_disagreement_safety_valve import (
    component_signs,
    fast_transition_multiplier,
    period_statistics,
    simulate_scaled_targets,
)
from trendbot.backtest import _target_weights, forward_mark_returns, performance_metrics
from trendbot.binance_archive import point_in_time_eligibility
from trendbot.config import TrendConfig
from trendbot.data import load_csv_panels


def scale_targets(targets: pd.DataFrame, multiplier: pd.DataFrame, delay: int) -> pd.DataFrame:
    return (targets * multiplier).shift(delay).fillna(0.0)


def comovement_regime(close: pd.DataFrame, window: int = 30) -> pd.Series:
    returns = close.pct_change(fill_method=None)
    market_mean = returns.mean(axis=1, skipna=True).abs()
    absolute_mean = returns.abs().mean(axis=1, skipna=True).replace(0.0, np.nan)
    daily_alignment = (market_mean / absolute_mean).clip(0.0, 1.0)
    # Shift makes the regime known before today's open.
    score = daily_alignment.rolling(window, min_periods=15).mean().shift(1)
    expanding_threshold = score.expanding(min_periods=180).quantile(0.75).shift(1)
    return (score >= expanding_threshold).fillna(False)


def attribution(
    positions: pd.DataFrame,
    daily: pd.DataFrame,
    opens: pd.DataFrame,
    closes: pd.DataFrame,
    high_comovement: pd.Series,
) -> dict:
    forward, _ = forward_mark_returns(opens, closes)
    forward = forward.reindex(index=positions.index, columns=positions.columns)
    gross = positions * forward
    by_market = gross.sum().sort_values(ascending=False)
    positive = float(by_market.clip(lower=0).sum())
    monthly = daily["net_return"].groupby(daily.index.to_period("M")).apply(lambda x: float((1 + x).prod() - 1))
    high = high_comovement.reindex(daily.index).fillna(False)
    long_gross = float(gross.where(positions > 0, 0.0).sum().sum())
    short_gross = float(gross.where(positions < 0, 0.0).sum().sum())
    return {
        "market_concentration": {
            "top_1_share_positive_gross": float(by_market.iloc[:1].clip(lower=0).sum() / positive) if positive else 0.0,
            "top_5_share_positive_gross": float(by_market.iloc[:5].clip(lower=0).sum() / positive) if positive else 0.0,
            "positive_markets": int((by_market > 0).sum()),
            "negative_markets": int((by_market < 0).sum()),
            "top_10": {str(k): float(v) for k, v in by_market.head(10).items()},
            "bottom_10": {str(k): float(v) for k, v in by_market.tail(10).items()},
        },
        "side_gross_contribution": {"long": long_gross, "short": short_gross},
        "months": {
            "best_10": {str(k): float(v) for k, v in monthly.nlargest(10).items()},
            "worst_10": {str(k): float(v) for k, v in monthly.nsmallest(10).items()},
            "2023": {str(k): float(v) for k, v in monthly[monthly.index.year == 2023].items()},
        },
        "correlation_regime": {
            "high_days": int(high.sum()),
            "normal_days": int((~high).sum()),
            "high_total_return": float((1 + daily.loc[high, "net_return"]).prod() - 1),
            "normal_total_return": float((1 + daily.loc[~high, "net_return"]).prod() - 1),
            "high_mean_daily_return": float(daily.loc[high, "net_return"].mean()),
            "normal_mean_daily_return": float(daily.loc[~high, "net_return"].mean()),
        },
    }


def summarize(daily: pd.DataFrame, config: TrendConfig) -> dict:
    return {
        "full": performance_metrics(daily, config),
        "2023": period_statistics(daily, "2023-01-01", "2023-12-31"),
        "2024_2025": period_statistics(daily, "2024-01-01", "2025-12-31"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panels = load_csv_panels(args.data)
    opens, closes, funding = panels["open"], panels["close"], panels["funding"]
    tradeable = point_in_time_eligibility(panels["quote_volume"], closes)
    base = TrendConfig()
    targets, _ = _target_weights(closes, base, tradeable)
    signs = component_signs(closes, base)
    multipliers = {
        "t1": pd.DataFrame(1.0, index=targets.index, columns=targets.columns),
        "fast_transition_50": fast_transition_multiplier(signs, 0.50),
        "fast_transition_75": fast_transition_multiplier(signs, 0.75),
    }
    high_comovement = comovement_regime(closes)
    results = {}
    for name, multiplier in multipliers.items():
        scaled = scale_targets(targets, multiplier, 0)
        config = replace(base, cost_bps=10.0)
        daily, positions = simulate_scaled_targets(
            scaled, pd.DataFrame(1.0, index=scaled.index, columns=scaled.columns),
            opens, closes, funding, tradeable, config,
        )
        results[name] = {
            "control": summarize(daily, config),
            "attribution": attribution(positions, daily, opens, closes, high_comovement),
            "stresses": {},
        }
        for delay in (1, 2):
            delayed = scale_targets(targets, multiplier, delay)
            stressed, _ = simulate_scaled_targets(
                delayed, pd.DataFrame(1.0, index=delayed.index, columns=delayed.columns),
                opens, closes, funding, tradeable, config,
            )
            results[name]["stresses"][f"additional_delay_{delay}d"] = summarize(stressed, config)
        for cost in (20.0, 30.0, 50.0):
            cost_config = replace(base, cost_bps=cost)
            stressed, _ = simulate_scaled_targets(
                scaled, pd.DataFrame(1.0, index=scaled.index, columns=scaled.columns),
                opens, closes, funding, tradeable, cost_config,
            )
            results[name]["stresses"][f"cost_{int(cost)}bps"] = summarize(stressed, cost_config)
        for mode in ("none", "adverse"):
            stressed, _ = simulate_scaled_targets(
                scaled, pd.DataFrame(1.0, index=scaled.index, columns=scaled.columns),
                opens, closes, funding, tradeable, config, funding_mode=mode,
            )
            results[name]["stresses"][f"funding_{mode}"] = summarize(stressed, config)
    payload = {
        "status": "frozen_finalist_falsification_audit",
        "method": "T1 and its frozen 50%/75% fast-transition valves. Extra execution delays are applied to the complete scaled target. Cost stresses are per unit turnover. Adverse funding charges the absolute observed rate against both long and short notional. High-correlation classification uses a lagged 30-day cross-sectional return-alignment score and an expanding 75th-percentile threshold.",
        "limitations": "All historical dates have been inspected. Correlation stress is conditional attribution, not a synthetic price shock. Venue-specific reproduction is still required.",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({name: {"control": data["control"], "stresses": data["stresses"]} for name, data in results.items()}, indent=2))


if __name__ == "__main__":
    main()
