from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from trendbot.config import TrendConfig
from trendbot.data import load_csv_directory
from trendbot.evaluation import ChronologicalSplit, evaluate_splits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--design-end", required=True)
    parser.add_argument("--validation-end", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    opens, closes, funding = load_csv_directory(args.data)
    split = ChronologicalSplit(args.design_end, args.validation_end)
    baseline = TrendConfig()
    variants = {
        "baseline": baseline,
        "long_only": replace(baseline, position_mode="long_only"),
        "short_only": replace(baseline, position_mode="short_only"),
        "binary": replace(baseline, response_kind="binary"),
        "linear": replace(baseline, response_kind="linear"),
        "fast_speed_only": replace(baseline, speeds=((16, 48),)),
        "medium_speed_only": replace(baseline, speeds=((32, 96),)),
        "slow_speed_only": replace(baseline, speeds=((64, 192),)),
        "no_buffer": replace(baseline, rebalance_buffer=0.0),
        "cost_20bps": replace(baseline, cost_bps=20.0),
    }
    output = {}
    for name, config in variants.items():
        result, reports = evaluate_splits(opens, closes, config, split, funding)
        output[name] = {
            "config": config.to_dict(),
            "full": result.metrics,
            "splits": reports,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({name: value["splits"] for name, value in output.items()}, indent=2))


if __name__ == "__main__":
    main()
