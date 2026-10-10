from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backtest import run_backtest
from .config import TrendConfig
from .data import load_csv_directory
from .evaluation import ChronologicalSplit, evaluate_splits


def main() -> None:
    parser = argparse.ArgumentParser(prog="trendbot")
    sub = parser.add_subparsers(dest="command", required=True)
    backtest = sub.add_parser("backtest", help="run the frozen baseline")
    backtest.add_argument("--data", type=Path, required=True)
    backtest.add_argument("--output", type=Path, required=True)
    backtest.add_argument("--design-end")
    backtest.add_argument("--validation-end")
    args = parser.parse_args()

    opens, closes, funding = load_csv_directory(args.data)
    config = TrendConfig()
    result = run_backtest(opens, closes, config, funding)
    splits = None
    if args.design_end or args.validation_end:
        if not args.design_end or not args.validation_end:
            parser.error("--design-end and --validation-end must be supplied together")
        result, splits = evaluate_splits(
            opens,
            closes,
            config,
            ChronologicalSplit(args.design_end, args.validation_end),
            funding,
        )
    payload = {
        "mode": "paper-research-only",
        "config": config.to_dict(),
        "markets": list(opens.columns),
        "start": str(opens.index.min()),
        "end": str(opens.index.max()),
        "metrics": result.metrics,
        "splits": splits,
        "attribution": result.attribution.to_dict(orient="index"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
