from __future__ import annotations

import argparse
import json
from pathlib import Path

from .backtest import run_backtest
from .config import TrendConfig
from .binance_archive import point_in_time_eligibility
from .data import load_csv_panels
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

    panels = load_csv_panels(args.data)
    opens, closes, funding = panels["open"], panels["close"], panels["funding"]
    tradeable = None
    if not panels["quote_volume"].empty:
        tradeable = point_in_time_eligibility(panels["quote_volume"], closes)
    config = TrendConfig()
    result = run_backtest(opens, closes, config, funding, tradeable)
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
            tradeable,
        )
    yearly = {
        str(year): {
            "return": float((1.0 + frame["net_return"]).prod() - 1.0),
            "turnover": float(frame["turnover"].sum()),
            "funding_return": float(frame["funding_return"].sum()),
            "cost_return": float(frame["cost_return"].sum()),
            "mean_gross_exposure": float(frame["gross_exposure"].mean()),
        }
        for year, frame in result.daily.groupby(result.daily.index.year)
    }
    gross_contributions = result.attribution["gross_return_contribution"].sort_values(
        ascending=False
    )
    positive_total = float(gross_contributions.clip(lower=0).sum())
    concentration = {
        "top_1_share_of_positive_gross": (
            float(gross_contributions.iloc[:1].clip(lower=0).sum() / positive_total)
            if positive_total else 0.0
        ),
        "top_5_share_of_positive_gross": (
            float(gross_contributions.iloc[:5].clip(lower=0).sum() / positive_total)
            if positive_total else 0.0
        ),
        "positive_markets": int((gross_contributions > 0).sum()),
        "negative_markets": int((gross_contributions < 0).sum()),
    }
    payload = {
        "mode": "paper-research-only",
        "config": config.to_dict(),
        "markets": list(opens.columns),
        "start": str(opens.index.min()),
        "end": str(opens.index.max()),
        "metrics": result.metrics,
        "splits": splits,
        "yearly": yearly,
        "concentration": concentration,
        "attribution": result.attribution.to_dict(orient="index"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "markets": len(opens.columns),
                "metrics": result.metrics,
                "splits": splits,
                "yearly": yearly,
                "concentration": concentration,
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
