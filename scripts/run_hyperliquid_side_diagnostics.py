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
    simulate_scaled_targets,
    summarize,
)
from scripts.run_hyperliquid_funded_attribution import contribution_matrices, grouped
from trendbot.backtest import _target_weights
from trendbot.binance_archive import point_in_time_eligibility
from trendbot.config import TrendConfig
from trendbot.data import load_csv_panels


def category_stats(
    labels: pd.DataFrame,
    positions: pd.DataFrame,
    matrices: dict[str, pd.DataFrame],
) -> dict[str, dict]:
    def with_exposure(mask: pd.DataFrame) -> dict[str, float]:
        result = grouped(mask, matrices)
        exposure = float(positions.abs().where(mask, 0.0).sum().sum())
        result["absolute_exposure_days"] = exposure
        result["net_per_100_exposure_days"] = (
            100.0 * result["net"] / exposure if exposure else 0.0
        )
        return result

    output = {}
    for label in sorted(str(value) for value in pd.unique(labels.to_numpy().ravel()) if pd.notna(value)):
        base = labels.eq(label)
        output[label] = {
            "all": with_exposure(base & positions.ne(0.0)),
            "long": with_exposure(base & (positions > 0)),
            "short": with_exposure(base & (positions < 0)),
            "held_market_days": int((base & positions.ne(0.0)).sum().sum()),
        }
    return output


def broadcast(series: pd.Series, columns: pd.Index) -> pd.DataFrame:
    return pd.DataFrame(
        np.broadcast_to(series.to_numpy()[:, None], (len(series), len(columns))),
        index=series.index,
        columns=columns,
    )


def causal_partitions(
    panels: dict[str, pd.DataFrame],
    positions: pd.DataFrame,
    slow_btc_sign: pd.Series,
) -> dict[str, pd.DataFrame]:
    closes = panels["close"].reindex(index=positions.index, columns=positions.columns)
    history = closes.notna().cumsum().shift(1).fillna(0)
    age = pd.DataFrame("unknown", index=positions.index, columns=positions.columns, dtype=object)
    age = age.mask((history >= 120) & (history <= 365), "120_365d")
    age = age.mask((history > 365) & (history <= 730), "366_730d")
    age = age.mask(history > 730, "over_730d")

    prior_liquidity = panels["quote_volume"].shift(1).rolling(30, min_periods=30).median()
    prior_liquidity = prior_liquidity.reindex(index=positions.index, columns=positions.columns)
    liquidity_rank = prior_liquidity.where(positions.ne(0.0)).rank(axis=1, pct=True)
    liquidity = pd.DataFrame("unknown", index=positions.index, columns=positions.columns, dtype=object)
    liquidity = liquidity.mask(liquidity_rank <= 1 / 3, "low_third")
    liquidity = liquidity.mask((liquidity_rank > 1 / 3) & (liquidity_rank <= 2 / 3), "middle_third")
    liquidity = liquidity.mask(liquidity_rank > 2 / 3, "high_third")

    btc = slow_btc_sign.reindex(positions.index).fillna(0.0)
    btc_label = pd.Series("neutral_or_unavailable", index=positions.index, dtype=object)
    btc_label = btc_label.mask(btc > 0, "btc_slow_bull")
    btc_label = btc_label.mask(btc < 0, "btc_slow_bear")

    expected_abs_funding = panels["funding"].abs().shift(1).rolling(7, min_periods=3).mean()
    expected_abs_funding = expected_abs_funding.reindex(index=positions.index, columns=positions.columns)
    burden_rank = expected_abs_funding.where(positions.ne(0.0)).rank(axis=1, pct=True)
    burden = pd.DataFrame("unknown", index=positions.index, columns=positions.columns, dtype=object)
    burden = burden.mask(burden_rank <= 1 / 3, "low_third")
    burden = burden.mask((burden_rank > 1 / 3) & (burden_rank <= 2 / 3), "middle_third")
    burden = burden.mask(burden_rank > 2 / 3, "high_third")
    return {
        "market_age": age,
        "prior_liquidity": liquidity,
        "btc_slow_regime": broadcast(btc_label, positions.columns),
        "prior_absolute_funding_burden": burden,
    }


def concentration(matrices: dict[str, pd.DataFrame]) -> dict[str, float | int]:
    by_market = matrices["net"].sum().sort_values(ascending=False)
    positive = by_market.clip(lower=0.0).sum()
    return {
        "positive_markets": int((by_market > 0).sum()),
        "negative_markets": int((by_market < 0).sum()),
        "top_1_share_positive_net": float(by_market.iloc[:1].clip(lower=0).sum() / positive) if positive else 0.0,
        "top_5_share_positive_net": float(by_market.iloc[:5].clip(lower=0).sum() / positive) if positive else 0.0,
        "net_after_removing_top_1": float(by_market.iloc[1:].sum()),
        "net_after_removing_top_5": float(by_market.iloc[5:].sum()),
    }


def high_liquidity_short_targets(
    targets: pd.DataFrame,
    quote_volume: pd.DataFrame,
    tradeable: pd.DataFrame,
) -> pd.DataFrame:
    """Keep all longs; keep shorts only in the causal top liquidity third."""
    prior_liquidity = quote_volume.shift(1).rolling(30, min_periods=30).median()
    liquidity_rank = prior_liquidity.where(tradeable).rank(axis=1, pct=True)
    return targets.where((targets >= 0.0) | (liquidity_rank > 2 / 3), 0.0)


def run_mode(
    mode: str,
    cost_bps: float,
    panels: dict[str, pd.DataFrame],
    tradeable: pd.DataFrame,
) -> tuple[dict, pd.DataFrame, dict[str, pd.DataFrame], list[pd.DataFrame]]:
    config = replace(TrendConfig(), position_mode=mode, cost_bps=cost_bps)
    targets, _ = _target_weights(panels["close"], config, tradeable)
    signs = component_signs(panels["close"], config)
    multiplier = fast_transition_multiplier(signs, 0.50)
    daily, positions = simulate_scaled_targets(
        targets, multiplier, panels["open"], panels["close"], panels["funding"], tradeable, config
    )
    matrices = contribution_matrices(
        positions, daily, panels["open"], panels["close"], panels["funding"], cost_bps
    )
    return {
        **summarize(daily, config),
        "arithmetic": grouped(positions.ne(0.0), matrices),
        "concentration": concentration(matrices),
    }, positions, matrices, signs


def run_liquid_short_hybrid(
    cost_bps: float,
    panels: dict[str, pd.DataFrame],
    tradeable: pd.DataFrame,
) -> dict:
    """Exploratory: retain all longs, but shorts only in the top liquidity third."""
    config = replace(TrendConfig(), position_mode="long_short", cost_bps=cost_bps)
    targets, _ = _target_weights(panels["close"], config, tradeable)
    signs = component_signs(panels["close"], config)
    multiplier = fast_transition_multiplier(signs, 0.50)
    hybrid_targets = high_liquidity_short_targets(
        targets, panels["quote_volume"], tradeable
    )
    daily, positions = simulate_scaled_targets(
        hybrid_targets, multiplier, panels["open"], panels["close"],
        panels["funding"], tradeable, config,
    )
    matrices = contribution_matrices(
        positions, daily, panels["open"], panels["close"], panels["funding"], cost_bps
    )
    return {
        **summarize(daily, config),
        "arithmetic": grouped(positions.ne(0.0), matrices),
        "concentration": concentration(matrices),
        "selection_warning": "Post-hoc exploratory hypothesis selected after inspecting cross-venue attribution; not validated or promotion-eligible.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--venue-label", default="Hyperliquid")
    parser.add_argument("--benchmark-symbol", default="BTC")
    args = parser.parse_args()
    panels = load_csv_panels(args.data)
    tradeable = point_in_time_eligibility(panels["quote_volume"], panels["close"])
    mode_results = {}
    diagnostic_source = None
    for cost in (10.0, 20.0, 30.0):
        for mode in ("long_short", "long_only", "short_only"):
            result, positions, matrices, signs = run_mode(mode, cost, panels, tradeable)
            mode_results[f"{mode}_{int(cost)}bps"] = result
            if mode == "long_short" and cost == 10.0:
                diagnostic_source = (positions, matrices, signs)
        mode_results[f"long_all_short_high_liquidity_exploratory_{int(cost)}bps"] = (
            run_liquid_short_hybrid(cost, panels, tradeable)
        )
    assert diagnostic_source is not None
    positions, matrices, signs = diagnostic_source
    if args.benchmark_symbol not in signs[-1].columns:
        raise ValueError(f"benchmark symbol not found: {args.benchmark_symbol}")
    partitions = causal_partitions(panels, positions, signs[-1][args.benchmark_symbol])
    partition_results = {
        name: category_stats(labels, positions, matrices)
        for name, labels in partitions.items()
    }
    payload = {
        "status": "frozen_50pct_side_diagnostic",
        "venue": args.venue_label,
        "benchmark_symbol": args.benchmark_symbol,
        "method": "The frozen 50% fast-transition rule is recomputed without parameter changes in long/short, long-only, and short-only modes at 10/20/30 bps. Long-only and short-only are diagnostic bounds, not selected candidates. Short-side attribution uses only causal market age, prior 30-day median liquidity, lagged benchmark 64/192 sign, and prior 7-day absolute funding burden.",
        "limitations": "The Hyperliquid history is already inspected. Partitions diagnose stability but cannot authorize choosing a favorable regime or side. Cost levels proxy additional execution friction; exact order-book slippage remains unmodeled.",
        "mode_bounds": mode_results,
        "causal_partitions_50pct_10bps": partition_results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({name: {
        "return": value["full"]["total_return"],
        "sharpe": value["full"]["sharpe"],
        "drawdown": value["full"]["max_drawdown"],
        "2023": value["folds"]["2023"]["return"],
        "2024_2025": value["folds"]["corroboration_2024_2025"]["return"],
        "without_top_5": value["concentration"]["net_after_removing_top_5"],
    } for name, value in mode_results.items()}, indent=2))


if __name__ == "__main__":
    main()
