from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from trendbot.backtest import _target_weights, forward_mark_returns, performance_metrics, run_backtest
from trendbot.binance_archive import point_in_time_eligibility
from trendbot.config import TrendConfig
from trendbot.data import load_csv_panels
from trendbot.signals import trend_signal


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


def component_signs(close: pd.DataFrame, config: TrendConfig) -> list[pd.DataFrame]:
    return [np.sign(trend_signal(close, replace(config, speeds=(speed,)))) for speed in config.speeds]


def consensus_multiplier(signs: list[pd.DataFrame], floor: float) -> pd.DataFrame:
    stack = np.stack([frame.to_numpy(dtype=float) for frame in signs])
    available = np.isfinite(stack) & (stack != 0)
    count = available.sum(axis=0)
    agreement = np.divide(
        np.abs(np.where(available, stack, 0.0).sum(axis=0)),
        count,
        out=np.ones_like(count, dtype=float),
        where=count > 0,
    )
    multiplier = floor + (1.0 - floor) * agreement
    return pd.DataFrame(multiplier, index=signs[0].index, columns=signs[0].columns)


def fast_transition_multiplier(signs: list[pd.DataFrame], floor: float) -> pd.DataFrame:
    fast = signs[0]
    slower = pd.concat(signs[1:], axis=0, keys=range(len(signs) - 1)).groupby(level=1).mean()
    conflict = fast.notna() & slower.notna() & (fast != 0) & (slower != 0) & (fast != np.sign(slower))
    return pd.DataFrame(np.where(conflict, floor, 1.0), index=fast.index, columns=fast.columns)


def slow_inertia_multiplier(
    signs: list[pd.DataFrame], targets: pd.DataFrame, floor: float
) -> pd.DataFrame:
    """Brake only a target still following slower sleeves after fast reversal."""
    fast = signs[0]
    slower = pd.concat(signs[1:], axis=0, keys=range(len(signs) - 1)).groupby(level=1).mean()
    slow_sign = np.sign(slower)
    target_sign = np.sign(targets)
    conflict = fast.notna() & slower.notna() & (fast != 0) & (slow_sign != 0) & (fast != slow_sign)
    stale = conflict & (target_sign == slow_sign)
    return pd.DataFrame(np.where(stale, floor, 1.0), index=fast.index, columns=fast.columns)


def simulate_scaled_targets(
    targets: pd.DataFrame,
    multiplier: pd.DataFrame,
    opens: pd.DataFrame,
    closes: pd.DataFrame,
    funding: pd.DataFrame,
    tradeable: pd.DataFrame,
    config: TrendConfig,
    funding_mode: str = "observed",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    positions = pd.DataFrame(0.0, index=opens.index[:-1], columns=opens.columns)
    forward, terminal = forward_mark_returns(opens, closes)
    current = np.zeros(len(opens.columns), dtype=float)
    equity = config.initial_equity
    records = []
    for i, date in enumerate(opens.index[:-1]):
        target = (targets.iloc[i] * multiplier.iloc[i]).to_numpy(dtype=float, copy=True)
        eligible = tradeable.iloc[i].to_numpy(dtype=bool)
        can_execute = opens.iloc[i].notna().to_numpy(dtype=bool)
        target = np.where(eligible, target, 0.0)
        gap = target - current
        tolerance = config.rebalance_buffer * np.abs(target)
        trade = np.where(np.abs(gap) > tolerance, gap - np.sign(gap) * tolerance, 0.0)
        trade = np.where((target == 0) & (current != 0), -current, trade)
        held = current + trade
        gross = float(np.abs(held).sum())
        if gross > config.max_gross_leverage:
            held *= config.max_gross_leverage / gross
        held = np.where(can_execute, held, current)
        next_return = forward.iloc[i].to_numpy(dtype=float)
        is_terminal = terminal.iloc[i].to_numpy(dtype=bool)
        turnover = float(np.abs(held - current).sum())
        turnover += float(np.nansum(np.where(is_terminal, np.abs(held * (1.0 + next_return)), 0.0)))
        cost_return = turnover * config.cost_bps / 10_000.0
        gross_return = float(np.nansum(held * next_return))
        funding_rate = funding.iloc[i].to_numpy(dtype=float)
        if funding_mode == "none":
            funding_return = 0.0
        elif funding_mode == "adverse":
            funding_return = float(np.nansum(np.abs(held) * np.abs(funding_rate)))
        elif funding_mode == "observed":
            funding_return = float(np.nansum(held * funding_rate))
        else:
            raise ValueError(f"unknown funding mode: {funding_mode}")
        net_return = gross_return - funding_return - cost_return
        equity *= 1.0 + net_return
        positions.iloc[i] = held
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
        drifted = held * (1.0 + np.nan_to_num(next_return))
        current = drifted / equity_factor if np.isfinite(equity_factor) and equity_factor > 0 else np.zeros_like(drifted)
        current = np.where(is_terminal, 0.0, current)
    return pd.DataFrame(records, index=opens.index[:-1]), positions


def period_statistics(daily: pd.DataFrame, start: str, end: str) -> dict[str, float]:
    frame = daily.loc[start:end]
    returns = frame["net_return"]
    curve = (1.0 + returns).cumprod()
    drawdown = curve / curve.cummax() - 1.0
    std = float(returns.std(ddof=1))
    return {
        "return": float(curve.iloc[-1] - 1.0),
        "sharpe": float(returns.mean() / std * np.sqrt(365)) if std > 0 else 0.0,
        "max_drawdown": float(drawdown.min()),
        "average_gross_exposure": float(frame["gross_exposure"].mean()),
        "turnover": float(frame["turnover"].sum()),
    }


def summarize(daily: pd.DataFrame, config: TrendConfig) -> dict:
    return {
        "full": performance_metrics(daily, config),
        "folds": {name: period_statistics(daily, start, end) for name, (start, end) in FOLDS.items()},
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
    floors = (0.0, 0.25, 0.50, 0.75)
    multiplier_sets = {
        **{f"consensus_floor_{int(floor * 100):02d}": consensus_multiplier(signs, floor) for floor in floors},
        **{f"fast_transition_floor_{int(floor * 100):02d}": fast_transition_multiplier(signs, floor) for floor in floors},
        **{f"slow_inertia_floor_{int(floor * 100):02d}": slow_inertia_multiplier(signs, targets, floor) for floor in floors},
    }
    variants = {}
    for cost in (10.0, 20.0):
        config = replace(base, cost_bps=cost)
        baseline = run_backtest(opens, closes, config, funding, tradeable)
        variants[f"baseline_{int(cost)}bps"] = summarize(baseline.daily, config)
        for name, multiplier in multiplier_sets.items():
            print(f"running {name}_{int(cost)}bps", flush=True)
            daily, _ = simulate_scaled_targets(targets, multiplier, opens, closes, funding, tradeable, config)
            summary = summarize(daily, config)
            active_target = targets.abs().sum(axis=1) > 0
            weighted_scale = (targets.abs() * multiplier).sum(axis=1) / targets.abs().sum(axis=1).replace(0, np.nan)
            summary["valve"] = {
                "affected_target_days_fraction": float(((weighted_scale < 0.999999) & active_target).mean()),
                "average_target_scale": float(weighted_scale[active_target].mean()),
            }
            variants[f"{name}_{int(cost)}bps"] = summary
    payload = {
        "status": "predeclared_research_counterfactual",
        "method": "Causal per-market exposure brake applied after T1 risk sizing. Consensus scales by signed agreement across available speed components; fast-transition scales whenever 16/48 opposes the mean sign of 32/96 and 64/192; slow-inertia scales only when that disagreement exists and the combined T1 target still follows the slower sign. Frozen floors: 0, 0.25, 0.50, 0.75. No return or price filter is used.",
        "evaluation_note": "All years have already been inspected and are corroborating rather than pristine holdouts. Promotion requires neighboring agreement, cost robustness, transition-loss improvement, and acceptable opportunity cost outside 2023.",
        "variants": variants,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({name: {"return": value["full"]["total_return"], "sharpe": value["full"]["sharpe"], "drawdown": value["full"]["max_drawdown"], "2023": value["folds"]["2023"]["return"], "2024_2025": value["folds"]["corroboration_2024_2025"]["return"]} for name, value in variants.items()}, indent=2))


if __name__ == "__main__":
    main()
