from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from trendbot.binance_archive import list_daily_archives, list_perpetual_symbols


def inspect(symbol: str) -> tuple[str, dict]:
    archives = list_daily_archives(symbol)
    keys = [str(item["key"]) for item in archives]
    months = [key.rsplit("-", 2)[-2] + "-" + key.rsplit("-", 1)[-1][:-4] for key in keys]
    return symbol, {
        "files": len(archives),
        "bytes": sum(int(item["size"]) for item in archives),
        "first_month": min(months) if months else None,
        "last_month": max(months) if months else None,
        "objects": archives,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/archive-manifest.json"))
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()
    symbols = list_perpetual_symbols("USDT")
    manifest = {}
    failures = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(inspect, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            try:
                symbol, entry = future.result()
                manifest[symbol] = entry
            except Exception as error:
                failures[futures[future]] = f"{type(error).__name__}: {error}"
    payload = {
        "symbol_count": len(manifest),
        "file_count": sum(item["files"] for item in manifest.values()),
        "total_bytes": sum(item["bytes"] for item in manifest.values()),
        "symbols": dict(sorted(manifest.items())),
        "failures": dict(sorted(failures.items())),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    summary = {key: payload[key] for key in ("symbol_count", "file_count", "total_bytes")}
    summary["failure_count"] = len(failures)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
