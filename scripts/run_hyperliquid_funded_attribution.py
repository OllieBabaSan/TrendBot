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


def contribution_matrices(
    positions: pd.DataFrame,
    daily: pd.DataFrame,
    opens: pd.DataFrame,
    closes: pd.DataFrame,
    funding: pd.DataFrame,
    cost_bps: float,
) -> dict[str, pd.DataFrame]:
    """Reconstruct the simulator's additive per-market return components."""
    forward, terminal = forward_mark_returns(opens, closes)
    forward = forward.reindex_like(positions)
    terminal = terminal.reindex_like(positions).fillna(False)
    rates = funding.reindex_like(positions).fillna(0.0)
    gross = positions * forward
    funding_cost = positions * rates
    turnover = pd.DataFrame(0.0, index=positions.index, columns=positions.columns)
    current = np.zeros(len(positions.columns), dtype=float)
    for i, date in enumerate(positions.index):
        held = positions.iloc[i].to_numpy(dtype=float)
        next_return = forward.iloc[i].to_numpy(dtype=float)
        is_terminal = terminal.iloc[i].to_numpy(dtype=bool)
        turnover.iloc[i] = np.abs(held - current) + np.where(
            is_terminal, np.abs(held * (1.0 + next_return)), 0.0
        )
        equity_factor = 1.0 + float(daily.iloc[i]["net_return"])
        drifted = held * (1.0 + np.nan_to_num(next_return))
        current = drifted / equity_factor if np.isfinite(equity_factor) and equity_factor > 0 else np.zeros_like(drifted)
        current = np.where(is_terminal, 0.0, current)
    trading_cost = turnover * cost_bps / 10_000.0
    net = gross - funding_cost - trading_cost
    return {
        "gross": gross,
        "funding_cost": funding_cost,
        "trading_cost": trading_cost,
        "net": net,
        "turnover": turnover,
    }


def grouped(mask: pd.DataFrame, matrices: dict[str, pd.DataFrame]) -> dict[str, float]:
    return {
        name: float(frame.where(mask, 0.0).sum().sum())
        for name, frame in matrices.items()
        if name != "turnover"
    } | {"turnover": float(matrices["turnover"].where(mask, 0.0).sum().sum())}


def market_table(matrices: dict[str, pd.DataFrame]) -> list[dict[str, float | str]]:
    rows = []
    for symbol in matrices["net"].columns:
        rows.append({
            "symbol": str(symbol),
            "gross": float(matrices["gross"][symbol].sum()),
            "funding_cost": float(matrices["funding_cost"][symbol].sum()),
            "trading_cost": float(matrices["trading_cost"][symbol].sum()),
            "net": float(matrices["net"][symbol].sum()),
            "turnover": float(matrices["turnover"][symbol].sum()),
        })
    return sorted(rows, key=lambda row: float(row["net"]), reverse=True)


def regime_table(mask: pd.Series, matrices: dict[str, pd.DataFrame]) -> dict[str, float | int]:
    selected = pd.DataFrame(
        np.broadcast_to(mask.reindex(matrices["net"].index).fillna(False).to_numpy()[:, None], matrices["net"].shape),
        index=matrices["net"].index,
        columns=matrices["net"].columns,
    )
    result = grouped(selected, matrices)
    result["days"] = int(mask.reindex(matrices["net"].index).fillna(False).sum())
    return result


def audit_variant(
    targets: pd.DataFrame,
    multiplier: pd.DataFrame,
    opens: pd.DataFrame,
    closes: pd.DataFrame,
    funding: pd.DataFrame,
    tradeable: pd.DataFrame,
    config: TrendConfig,
) -> dict:
    daily, positions = simulate_scaled_targets(
        targets, multiplier, opens, closes, funding, tradeable, config
    )
    matrices = contribution_matrices(positions, daily, opens, closes, funding, config.cost_bps)
    markets = market_table(matrices)
    positive = sum(max(float(row["net"]), 0.0) for row in markets)
    disagreement = (multiplier < 0.999999) & positions.ne(0.0)
    paying = matrices["funding_cost"] > 0
    receiving = matrices["funding_cost"] < 0
    monthly = matrices["net"].sum(axis=1).groupby(matrices["net"].index.to_period("M")).sum()
    yearly = matrices["net"].sum(axis=1).groupby(matrices["net"].index.year).sum()
    reconstruction_error = float((matrices["net"].sum(axis=1) - daily["net_return"]).abs().max())
    periods = {
        "2023": ("2023-01-01", "2023-12-31"),
        "2024": ("2024-01-01", "2024-12-31"),
        "2025": ("2025-01-01", "2025-12-31"),
        "2026": ("2026-01-01", "2026-12-31"),
        "2024_2025": ("2024-01-01", "2025-12-31"),
    }
    period_attribution = {}
    for name, (start, end) in periods.items():
        in_period = pd.Series(
            (positions.index >= pd.Timestamp(start, tz="UTC"))
            & (positions.index <= pd.Timestamp(end, tz="UTC")),
            index=positions.index,
        )
        date_mask = pd.DataFrame(
            np.broadcast_to(in_period.to_numpy()[:, None], positions.shape),
            index=positions.index,
            columns=positions.columns,
        )
        period_attribution[name] = {
            "all": grouped(date_mask, matrices),
            "long": grouped(date_mask & (positions > 0), matrices),
            "short": grouped(date_mask & (positions < 0), matrices),
        }
    return {
        "headline": {
            **performance_metrics(daily, config),
            "2023": period_statistics(daily, "2023-01-01", "2023-12-31"),
            "2024_2025": period_statistics(daily, "2024-01-01", "2025-12-31"),
        },
        "arithmetic_components": grouped(pd.DataFrame(True, index=positions.index, columns=positions.columns), matrices),
        "side": {
            "long": grouped(positions > 0, matrices),
            "short": grouped(positions < 0, matrices),
            "flat_or_transition": grouped(positions == 0, matrices),
        },
        "funding_state": {
            "paying": grouped(paying, matrices),
            "receiving": grouped(receiving, matrices),
            "zero": grouped(~paying & ~receiving, matrices),
        },
        "transition_state": {
            "disagreement": grouped(disagreement, matrices),
            "agreement": grouped(~disagreement & positions.ne(0.0), matrices),
        },
        "calendar": {
            "yearly_arithmetic_net": {str(k): float(v) for k, v in yearly.items()},
            "best_months": {str(k): float(v) for k, v in monthly.nlargest(10).items()},
            "worst_months": {str(k): float(v) for k, v in monthly.nsmallest(10).items()},
            "period_attribution": period_attribution,
        },
        "market_concentration": {
            "positive_markets": sum(float(row["net"]) > 0 for row in markets),
            "negative_markets": sum(float(row["net"]) < 0 for row in markets),
            "top_1_share_positive_net": max(float(markets[0]["net"]), 0.0) / positive if positive else 0.0,
            "top_5_share_positive_net": sum(max(float(row["net"]), 0.0) for row in markets[:5]) / positive if positive else 0.0,
            "net_after_removing_top_1": float(matrices["net"].sum().sum() - float(markets[0]["net"])),
            "net_after_removing_top_5": float(matrices["net"].sum().sum() - sum(float(row["net"]) for row in markets[:5])),
            "top_15": markets[:15],
            "bottom_15": markets[-15:],
            "all_markets": markets,
        },
        "reconstruction_max_abs_error": reconstruction_error,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panels = load_csv_panels(args.data)
    opens, closes, funding = panels["open"], panels["close"], panels["funding"]
    tradeable = point_in_time_eligibility(panels["quote_volume"], closes)
    config = replace(TrendConfig(), cost_bps=10.0)
    targets, _ = _target_weights(closes, config, tradeable)
    signs = component_signs(closes, config)
    variants = {
        "t1": pd.DataFrame(1.0, index=targets.index, columns=targets.columns),
        "fast_transition_50": fast_transition_multiplier(signs, 0.50),
        "fast_transition_75": fast_transition_multiplier(signs, 0.75),
    }
    results = {
        name: audit_variant(targets, multiplier, opens, closes, funding, tradeable, config)
        for name, multiplier in variants.items()
    }
    payload = {
        "status": "frozen_hyperliquid_funded_attribution",
        "method": "Exact additive decomposition of the unchanged 10-bps funded T1 and frozen 50%/75% fast-transition candidates by market, side, funding state, disagreement state, and calendar period. Headline returns remain compounded portfolio returns.",
        "limitations": "This is diagnosis on an already inspected historical venue sample, not a tuning or promotion exercise. Per-market net contributions are arithmetic return contributions and do not allocate cross-time compounding.",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({name: {
        "return": item["headline"]["total_return"],
        "sharpe": item["headline"]["sharpe"],
        "funding_cost": item["arithmetic_components"]["funding_cost"],
        "long_net": item["side"]["long"]["net"],
        "short_net": item["side"]["short"]["net"],
        "top_5_share": item["market_concentration"]["top_5_share_positive_net"],
        "reconstruction_error": item["reconstruction_max_abs_error"],
    } for name, item in results.items()}, indent=2))


if __name__ == "__main__":
    main()
