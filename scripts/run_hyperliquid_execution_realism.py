from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.run_disagreement_safety_valve import (
    component_signs,
    fast_transition_multiplier,
    summarize,
)
from scripts.run_hyperliquid_side_diagnostics import high_liquidity_short_targets
from trendbot.backtest import _target_weights, forward_mark_returns
from trendbot.binance_archive import point_in_time_eligibility
from trendbot.config import TrendConfig
from trendbot.data import load_csv_panels


@dataclass(frozen=True)
class ExecutionAssumptions:
    initial_equity: float = 5_000.0
    taker_fee_bps: float = 4.5
    slippage_floor_bps: float = 1.0
    impact_coefficient: float = 0.5
    minimum_notional: float = 10.0
    delay_days: int = 0


def load_lot_sizes(manifest_path: Path, columns: pd.Index) -> pd.Series:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_file = {
        Path(item["file"]).stem.upper(): 10.0 ** (-int(item["sz_decimals"]))
        for item in manifest["markets"].values()
        if item.get("status") == "ok" and item.get("file") and "sz_decimals" in item
    }
    missing = [str(column) for column in columns if str(column) not in by_file]
    if missing:
        raise ValueError(f"missing lot-size metadata: {missing[:10]}")
    return pd.Series({column: by_file[str(column)] for column in columns}, dtype=float)


def round_toward_zero(values: np.ndarray, increments: np.ndarray) -> np.ndarray:
    return np.trunc(values / increments) * increments


def simulate_executable_targets(
    scaled_targets: pd.DataFrame,
    opens: pd.DataFrame,
    closes: pd.DataFrame,
    funding: pd.DataFrame,
    quote_volume: pd.DataFrame,
    tradeable: pd.DataFrame,
    lot_sizes: pd.Series,
    config: TrendConfig,
    assumptions: ExecutionAssumptions,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float | int]]:
    targets = scaled_targets.shift(assumptions.delay_days).fillna(0.0)
    positions = pd.DataFrame(0.0, index=opens.index[:-1], columns=opens.columns)
    forward, terminal = forward_mark_returns(opens, closes)
    prior_volume = quote_volume.shift(1).rolling(30, min_periods=30).median()
    prior_abs_return = closes.pct_change(fill_method=None).abs().shift(1).rolling(30, min_periods=20).median()
    lots = lot_sizes.reindex(opens.columns).to_numpy(dtype=float)
    current = np.zeros(len(opens.columns), dtype=float)
    equity = assumptions.initial_equity
    records = []
    rejected_minimum_orders = 0
    rounded_orders = 0
    requested_orders = 0
    skipped_notional = 0.0
    impact_cost_dollars = 0.0
    fee_cost_dollars = 0.0
    tracking_errors: list[float] = []
    total_turnover = 0.0
    total_cost_return = 0.0
    for i, date in enumerate(opens.index[:-1]):
        target = targets.iloc[i].to_numpy(dtype=float, copy=True)
        eligible = tradeable.iloc[i].to_numpy(dtype=bool)
        prices = opens.iloc[i].to_numpy(dtype=float)
        can_execute = np.isfinite(prices) & (prices > 0)
        target = np.where(eligible, target, 0.0)
        gap = target - current
        tolerance = config.rebalance_buffer * np.abs(target)
        ideal_trade = np.where(np.abs(gap) > tolerance, gap - np.sign(gap) * tolerance, 0.0)
        ideal_trade = np.where((target == 0) & (current != 0), -current, ideal_trade)
        tentative = current + ideal_trade
        gross = float(np.abs(tentative).sum())
        if gross > config.max_gross_leverage:
            tentative *= config.max_gross_leverage / gross
            ideal_trade = tentative - current
        requested_orders += int((np.abs(ideal_trade) > 0).sum())
        desired_units = np.divide(
            ideal_trade * equity,
            prices,
            out=np.zeros_like(ideal_trade),
            where=can_execute,
        )
        executable_units = round_toward_zero(desired_units, lots)
        rounded_orders += int((np.abs(executable_units - desired_units) > 1e-12).sum())
        notionals = np.abs(executable_units * prices)
        too_small = (notionals > 0) & (notionals < assumptions.minimum_notional)
        rejected_minimum_orders += int(too_small.sum())
        skipped_notional += float(notionals[too_small].sum())
        executable_units = np.where(too_small, 0.0, executable_units)
        trade_weights = np.divide(
            executable_units * prices,
            equity,
            out=np.zeros_like(executable_units),
            where=can_execute,
        )
        held = current + trade_weights
        tracking_errors.append(float(np.abs(held - target).sum()))
        next_return = forward.iloc[i].to_numpy(dtype=float)
        is_terminal = terminal.iloc[i].to_numpy(dtype=bool)
        terminal_weights = np.where(is_terminal, np.abs(held * (1.0 + np.nan_to_num(next_return))), 0.0)
        turnover_by_market = np.abs(trade_weights) + terminal_weights
        fee_return = float(turnover_by_market.sum() * assumptions.taker_fee_bps / 10_000.0)
        volume = prior_volume.iloc[i].to_numpy(dtype=float)
        volatility = prior_abs_return.iloc[i].to_numpy(dtype=float)
        trade_notional = turnover_by_market * equity
        participation = np.divide(
            trade_notional,
            volume,
            out=np.zeros_like(trade_notional),
            where=np.isfinite(volume) & (volume > 0),
        )
        impact_fraction = assumptions.impact_coefficient * np.nan_to_num(volatility) * np.sqrt(np.maximum(participation, 0.0))
        impact_fraction += assumptions.slippage_floor_bps / 10_000.0
        slippage_return = float(np.sum(turnover_by_market * impact_fraction))
        total_turnover += float(turnover_by_market.sum())
        total_cost_return += fee_return + slippage_return
        gross_return = float(np.nansum(held * next_return))
        funding_rate = funding.iloc[i].to_numpy(dtype=float)
        funding_return = float(np.nansum(held * funding_rate))
        net_return = gross_return - funding_return - fee_return - slippage_return
        fee_cost_dollars += fee_return * equity
        impact_cost_dollars += slippage_return * equity
        equity *= 1.0 + net_return
        positions.iloc[i] = held
        records.append({
            "equity": equity,
            "gross_return": gross_return,
            "funding_return": funding_return,
            "cost_return": fee_return + slippage_return,
            "fee_return": fee_return,
            "slippage_return": slippage_return,
            "net_return": net_return,
            "turnover": float(turnover_by_market.sum()),
            "gross_exposure": float(np.abs(held).sum()),
            "net_exposure": float(held.sum()),
        })
        equity_factor = 1.0 + net_return
        drifted = held * (1.0 + np.nan_to_num(next_return))
        current = drifted / equity_factor if np.isfinite(equity_factor) and equity_factor > 0 else np.zeros_like(drifted)
        current = np.where(is_terminal, 0.0, current)
    diagnostics = {
        "requested_orders": requested_orders,
        "orders_affected_by_rounding": rounded_orders,
        "orders_rejected_below_minimum": rejected_minimum_orders,
        "cumulative_repeated_subminimum_notional_dollars": skipped_notional,
        "minimum_rejection_fraction_of_requested_orders": (
            rejected_minimum_orders / requested_orders if requested_orders else 0.0
        ),
        "average_absolute_target_tracking_error": float(np.mean(tracking_errors)),
        "maximum_absolute_target_tracking_error": float(np.max(tracking_errors)),
        "effective_all_in_execution_cost_bps": (
            10_000.0 * total_cost_return / total_turnover if total_turnover else 0.0
        ),
        "fee_cost_dollars_path_dependent": fee_cost_dollars,
        "slippage_cost_dollars_path_dependent": impact_cost_dollars,
        "ending_equity": equity,
    }
    return pd.DataFrame(records, index=opens.index[:-1]), positions, diagnostics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panels = load_csv_panels(args.data)
    opens, closes = panels["open"], panels["close"]
    tradeable = point_in_time_eligibility(panels["quote_volume"], closes)
    base = TrendConfig()
    targets, _ = _target_weights(closes, base, tradeable)
    signs = component_signs(closes, base)
    valve = fast_transition_multiplier(signs, 0.50)
    long_config = replace(base, position_mode="long_only")
    long_targets, _ = _target_weights(closes, long_config, tradeable)
    long_signs = component_signs(closes, long_config)
    variants = {
        "t1": targets,
        "fast_transition_50": targets * valve,
        "long_only_boundary": long_targets * fast_transition_multiplier(long_signs, 0.50),
        "liquid_short_hybrid": high_liquidity_short_targets(
            targets, panels["quote_volume"], tradeable
        ) * valve,
    }
    lot_sizes = load_lot_sizes(args.manifest, opens.columns)
    scenarios = {
        "venue_base_5k": ExecutionAssumptions(),
        "impact_stress_5k": ExecutionAssumptions(impact_coefficient=1.0),
        "delay_1d_5k": ExecutionAssumptions(delay_days=1),
        "small_account_2500": ExecutionAssumptions(initial_equity=2_500.0),
        "reference_10000": ExecutionAssumptions(initial_equity=10_000.0),
    }
    plan = [
        ("t1", "venue_base_5k"),
        ("fast_transition_50", "venue_base_5k"),
        ("long_only_boundary", "venue_base_5k"),
        ("liquid_short_hybrid", "venue_base_5k"),
        ("fast_transition_50", "impact_stress_5k"),
        ("liquid_short_hybrid", "impact_stress_5k"),
        ("fast_transition_50", "delay_1d_5k"),
        ("liquid_short_hybrid", "delay_1d_5k"),
        ("liquid_short_hybrid", "small_account_2500"),
        ("liquid_short_hybrid", "reference_10000"),
    ]
    results = {}
    for variant_name, scenario_name in plan:
        assumptions = scenarios[scenario_name]
        metric_config = replace(
            base, cost_bps=0.0, initial_equity=assumptions.initial_equity
        )
        daily, _, diagnostics = simulate_executable_targets(
            variants[variant_name], opens, closes, panels["funding"],
            panels["quote_volume"], tradeable, lot_sizes, metric_config, assumptions,
        )
        results[f"{variant_name}__{scenario_name}"] = {
            **summarize(daily, metric_config),
            "execution": diagnostics,
            "assumptions": assumptions.__dict__,
        }
    payload = {
        "status": "hyperliquid_execution_realism_gate",
        "method": "Daily next-open simulation with frozen signals; Hyperliquid lot rounding and $10 minimum orders; base-tier 4.5-bps taker fee; causal square-root impact using prior 30-day median absolute return and quote volume; 1-bps slippage floor. Impact coefficients are scenario assumptions, not observed historical order-book fills.",
        "limitations": "Historical L2 order books are unavailable. Current szDecimals metadata is applied historically. Exact market-order fills, queueing, and historical fee-tier changes are not reconstructed.",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({name: {
        "return": value["full"]["total_return"],
        "sharpe": value["full"]["sharpe"],
        "drawdown": value["full"]["max_drawdown"],
        "2023": value["folds"]["2023"]["return"],
        "2024_2025": value["folds"]["corroboration_2024_2025"]["return"],
        "rejected_orders": value["execution"]["orders_rejected_below_minimum"],
        "ending_equity": value["execution"]["ending_equity"],
    } for name, value in results.items()}, indent=2))


if __name__ == "__main__":
    main()
