from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from trendbot.data import load_csv_panels
from trendbot.clustering import average_linkage_labels


PERIODS = {
    "2020": ("2020-01-01", "2020-12-31"),
    "2021": ("2021-01-01", "2021-12-31"),
    "2022": ("2022-01-01", "2022-12-31"),
    "2023": ("2023-01-01", "2023-12-31"),
    "2024": ("2024-01-01", "2024-12-31"),
    "2025": ("2025-01-01", "2025-12-31"),
    "design_2020_2022": ("2020-01-01", "2022-12-31"),
    "corroboration_2024_2025": ("2024-01-01", "2025-12-31"),
}


def load_reference(path: Path):
    # The managed Windows environment may not load a newly downloaded SciPy
    # binary. Supply only the three hierarchy APIs used by the reference,
    # backed by TrendBot's tested dependency-free average-linkage equivalent.
    hierarchy = types.ModuleType("scipy.cluster.hierarchy")
    distance = types.ModuleType("scipy.spatial.distance")
    hierarchy.linkage = lambda matrix, method="average": matrix
    hierarchy.fcluster = lambda matrix, t, criterion="maxclust": (
        average_linkage_labels(1.0 - np.square(matrix) / 2.0, int(t)) + 1
    )
    distance.squareform = lambda matrix, checks=False: matrix
    scipy = types.ModuleType("scipy")
    cluster = types.ModuleType("scipy.cluster")
    spatial = types.ModuleType("scipy.spatial")
    sys.modules.update({
        "scipy": scipy,
        "scipy.cluster": cluster,
        "scipy.cluster.hierarchy": hierarchy,
        "scipy.spatial": spatial,
        "scipy.spatial.distance": distance,
    })
    spec = importlib.util.spec_from_file_location("trend_atlas_reference_engine", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import reference engine from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def period_summary(engine, daily: pd.DataFrame, start: str, end: str) -> dict:
    frame = daily.loc[start:end]
    return engine.performance_summary(frame) if len(frame) else {"days": 0}


def run_variant(engine, panels, config) -> dict:
    inputs = engine.prepare_inputs(panels, config)
    result = engine.simulate(
        opens=inputs.opens,
        closes=inputs.closes,
        signal=inputs.signal,
        annual_vol=inputs.annual_vol,
        tradeable=inputs.tradeable,
        funding=inputs.funding,
        log_returns=inputs.log_returns,
        config=config,
    )
    return {
        "config": engine.config_dict(config),
        "full": engine.performance_summary(result.daily),
        "periods": {
            name: period_summary(engine, result.daily, start, end)
            for name, (start, end) in PERIODS.items()
        },
        "diagnostics": {
            "maximum_gross_exposure_ratio": float(
                (result.daily["gross_exposure"] / result.daily["start_equity"]).max()
            ),
            "correlation_rebuilds": int(len(result.diagnostics)),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--reference-engine", type=Path, required=True)
    parser.add_argument("--reference-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    engine = load_reference(args.reference_engine)
    loaded = load_csv_panels(args.data)
    # The upstream engine's Config dates are timezone-naive. All archive rows
    # are UTC, so remove only the timezone label without shifting timestamps.
    loaded = {
        name: frame.set_axis(frame.index.tz_localize(None), axis=0)
        for name, frame in loaded.items()
    }
    complete = loaded["open"].notna() & loaded["close"].notna()
    panels = {
        **loaded,
        # The archive assembler emits one daily row only when that daily kline
        # exists. Intraday completeness was not retained, so an observed daily
        # bar is represented as complete for this like-for-like experiment.
        "hours": complete.astype(np.int16) * 24,
    }
    default = engine.Config(start="2020-01-01", end="2025-12-31")
    variants = {
        "reference_full": default,
        "reference_cap_1_5": replace(default, max_gross_leverage=1.5),
        "reference_no_clusters_cap_1_5": replace(
            default, max_gross_leverage=1.5, use_sector_weights=False
        ),
        "reference_short_vol_no_clusters_cap_1_5": replace(
            default,
            max_gross_leverage=1.5,
            use_sector_weights=False,
            vol_forecast="short",
        ),
        "reference_no_clusters_cap_2_0": replace(default, use_sector_weights=False),
    }
    payload = {
        "reference": {
            "repository": "https://github.com/0xpg/crypto-trend-following",
            "commit": args.reference_commit,
            "engine_file": str(args.reference_engine),
            "dependency_note": "The reference engine is unchanged. Its SciPy linkage calls are serviced by TrendBot's tested dependency-free implementation of the same average-linkage correlation-distance rule because managed Windows blocked the downloaded SciPy DLL.",
        },
        "data_note": "Observed assembled daily bars are represented as 24-hour-complete because the daily CSVs do not retain intraday completeness counts.",
        "status": "research_reproduction_not_automatically_promoted",
        "variants": {
            name: run_variant(engine, panels, config) for name, config in variants.items()
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        name: {
            "total": result["full"]["total_return"],
            "sharpe": result["full"]["sharpe_net"],
            "max_drawdown": result["full"]["max_drawdown"],
            "2023": result["periods"]["2023"]["total_return"],
            "2024_2025": result["periods"]["corroboration_2024_2025"]["total_return"],
        }
        for name, result in payload["variants"].items()
    }, indent=2))


if __name__ == "__main__":
    main()
