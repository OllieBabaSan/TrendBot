from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from trendbot.backtest import forward_mark_returns, run_backtest
from trendbot.binance_archive import point_in_time_eligibility
from trendbot.clustering import average_linkage_labels
from trendbot.config import TrendConfig
from trendbot.data import load_csv_panels


PERIODS = {
    "2023": ("2023-01-01", "2023-12-31"),
    "2023-01": ("2023-01-01", "2023-01-31"),
    "2023-03": ("2023-03-01", "2023-03-31"),
}


def compound(series: pd.Series) -> float:
    return float((1.0 + series.fillna(0.0)).prod() - 1.0)


def position_ages(positions: pd.DataFrame) -> pd.DataFrame:
    values = positions.to_numpy(dtype=float)
    ages = np.zeros(values.shape, dtype=np.int32)
    previous_sign = np.zeros(values.shape[1], dtype=np.int8)
    previous_age = np.zeros(values.shape[1], dtype=np.int32)
    for row in range(values.shape[0]):
        sign = np.sign(values[row]).astype(np.int8)
        active = sign != 0
        same = active & (sign == previous_sign)
        current_age = np.where(active, np.where(same, previous_age + 1, 1), 0)
        ages[row] = current_age
        previous_sign, previous_age = sign, current_age
    return pd.DataFrame(ages, index=positions.index, columns=positions.columns)


def contribution_frames(result, opens: pd.DataFrame, closes: pd.DataFrame, funding: pd.DataFrame):
    positions = result.positions
    forward, _ = forward_mark_returns(opens, closes)
    forward = forward.reindex(index=positions.index, columns=positions.columns)
    funding = funding.reindex(index=positions.index, columns=positions.columns).fillna(0.0)
    gross = (positions * forward).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    funding_cost = (positions * funding).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return positions, gross, funding_cost


def directional_attribution(positions, gross, funding_cost, start, end):
    mask = (positions.index >= start) & (positions.index <= end)
    p, g, f = positions.loc[mask], gross.loc[mask], funding_cost.loc[mask]
    return {
        "long_gross": float(g.where(p > 0, 0.0).to_numpy().sum()),
        "long_funding_cost": float(f.where(p > 0, 0.0).to_numpy().sum()),
        "short_gross": float(g.where(p < 0, 0.0).to_numpy().sum()),
        "short_funding_cost": float(f.where(p < 0, 0.0).to_numpy().sum()),
    }


def age_attribution(positions, gross, funding_cost, start, end):
    ages = position_ages(positions)
    mask = (positions.index >= start) & (positions.index <= end)
    buckets = {"1-3": (1, 3), "4-10": (4, 10), "11-30": (11, 30), "31-90": (31, 90), "91+": (91, 10**9)}
    answer = {}
    for name, (low, high) in buckets.items():
        selected = (ages.loc[mask] >= low) & (ages.loc[mask] <= high)
        answer[name] = {
            "gross": float(gross.loc[mask].where(selected, 0.0).to_numpy().sum()),
            "funding_cost": float(funding_cost.loc[mask].where(selected, 0.0).to_numpy().sum()),
            "position_days": int(selected.to_numpy().sum()),
        }
    return answer


def fixed_preperiod_clusters(closes: pd.DataFrame, columns: pd.Index, n_clusters: int = 8):
    returns = closes[columns].pct_change(fill_method=None).loc["2022-07-01":"2022-12-31"]
    keep = returns.notna().sum() >= 100
    returns = returns.loc[:, keep]
    corr = returns.corr(min_periods=100)
    array = corr.to_numpy(dtype=float)
    off = ~np.eye(len(array), dtype=bool)
    mean = float(np.nanmean(array[off])) if np.isfinite(array[off]).any() else 0.0
    array = np.where(np.isfinite(array), array, mean)
    target = np.full_like(array, mean)
    np.fill_diagonal(target, 1.0)
    array = 0.7 * array + 0.3 * target
    labels = average_linkage_labels(array, n_clusters)
    return dict(zip(returns.columns, labels, strict=True))


def cluster_attribution(mapping, positions, gross, funding_cost, start, end):
    mask = (positions.index >= start) & (positions.index <= end)
    rows = []
    for label in sorted(set(mapping.values())):
        symbols = [symbol for symbol, value in mapping.items() if value == label]
        market_net = gross.loc[mask, symbols].sum() - funding_cost.loc[mask, symbols].sum()
        contributors = market_net.sort_values()
        rows.append({
            "cluster": int(label),
            "markets": len(symbols),
            "gross": float(gross.loc[mask, symbols].to_numpy().sum()),
            "funding_cost": float(funding_cost.loc[mask, symbols].to_numpy().sum()),
            "worst_markets": {k: float(v) for k, v in contributors.head(5).items()},
            "representative_markets": symbols[:12],
        })
    return rows


def speed_results(opens, closes, funding, tradeable, config):
    answer = {}
    for fast, slow in config.speeds:
        result = run_backtest(opens, closes, replace(config, speeds=((fast, slow),)), funding, tradeable)
        answer[f"{fast}_{slow}"] = {
            name: {
                "net_return": compound(result.daily.loc[start:end, "net_return"]),
                "gross_return_sum": float(result.daily.loc[start:end, "gross_return"].sum()),
                "cost_return_sum": float(result.daily.loc[start:end, "cost_return"].sum()),
                "funding_return_sum": float(result.daily.loc[start:end, "funding_return"].sum()),
            }
            for name, (start, end) in PERIODS.items()
        }
    return answer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panels = load_csv_panels(args.data)
    opens, closes, funding = panels["open"], panels["close"], panels["funding"]
    tradeable = point_in_time_eligibility(panels["quote_volume"], closes)
    config = TrendConfig()
    result = run_backtest(opens, closes, config, funding, tradeable)
    positions, gross, funding_cost = contribution_frames(result, opens, closes, funding)
    mapping = fixed_preperiod_clusters(closes, positions.columns)

    period_summary = {}
    for name, (start, end) in PERIODS.items():
        daily = result.daily.loc[start:end]
        market_net = gross.loc[start:end].sum() - funding_cost.loc[start:end].sum()
        period_summary[name] = {
            "net_return": compound(daily["net_return"]),
            "gross_return_sum": float(daily["gross_return"].sum()),
            "cost_return_sum": float(daily["cost_return"].sum()),
            "funding_return_sum": float(daily["funding_return"].sum()),
            "average_gross_exposure": float(daily["gross_exposure"].mean()),
            "direction": directional_attribution(positions, gross, funding_cost, start, end),
            "position_age": age_attribution(positions, gross, funding_cost, start, end),
            "clusters": cluster_attribution(mapping, positions, gross, funding_cost, start, end),
            "worst_markets": {k: float(v) for k, v in market_net.nsmallest(15).items()},
            "best_markets": {k: float(v) for k, v in market_net.nlargest(15).items()},
        }

    payload = {
        "method": {
            "purpose": "Attribution only; no rule was selected or fitted from 2023.",
            "cluster_formation_window": "2022-07-01 through 2022-12-31, fixed before 2023",
            "cluster_count": 8,
            "cost_note": "Trading costs are reported at portfolio level and are not arbitrarily assigned to markets, ages, or clusters.",
        },
        "periods": period_summary,
        "single_speed_counterfactuals": speed_results(opens, closes, funding, tradeable, config),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "periods": {k: v["net_return"] for k, v in period_summary.items()}}, indent=2))


if __name__ == "__main__":
    main()
