from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from trendbot.binance_archive import point_in_time_eligibility
from trendbot.config import TrendConfig
from trendbot.data import load_csv_panels
from trendbot.evaluation import ChronologicalSplit, evaluate_splits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--design-end", required=True)
    parser.add_argument("--validation-end", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panels = load_csv_panels(args.data)
    opens, closes, funding = panels["open"], panels["close"], panels["funding"]
    tradeable = point_in_time_eligibility(panels["quote_volume"], closes)
    split = ChronologicalSplit(args.design_end, args.validation_end)
    control = TrendConfig()
    variants = {
        "control": control,
        "cluster_8": replace(control, use_cluster_weights=True, n_clusters=8),
        "cluster_4": replace(control, use_cluster_weights=True, n_clusters=4),
        "cluster_12": replace(control, use_cluster_weights=True, n_clusters=12),
        "cluster_8_cost_20bps": replace(
            control, use_cluster_weights=True, n_clusters=8, cost_bps=20.0
        ),
    }
    output = {}
    for name, config in variants.items():
        result, reports = evaluate_splits(
            opens, closes, config, split, funding, tradeable
        )
        output[name] = {
            "config": config.to_dict(),
            "full": result.metrics,
            "splits": reports,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
