from __future__ import annotations

import argparse
import json
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from trendbot.binance_archive import ARCHIVE_ROOT, download, read_daily_klines, read_funding


def month_from_key(key: str) -> str:
    stem = Path(key).stem
    return "-".join(stem.rsplit("-", 2)[-2:])


def funding_url(symbol: str, month: str) -> str:
    name = f"{symbol}-fundingRate-{month}.zip"
    return f"{ARCHIVE_ROOT}/fundingRate/{symbol}/{name}"


def fetch_one(url: str, path: Path) -> tuple[str, str | None]:
    if path.exists():
        return str(path), None
    try:
        download(url, path)
        return str(path), None
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return str(path), "404"
        return str(path), f"HTTP {error.code}"
    except Exception as error:
        return str(path), f"{type(error).__name__}: {error}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--cache", type=Path, default=Path("data/universe-archive"))
    parser.add_argument("--output", type=Path, default=Path("data/universe-csv"))
    parser.add_argument("--workers", type=int, default=32)
    args = parser.parse_args()
    catalog = json.loads(args.manifest.read_text(encoding="utf-8"))["symbols"]
    jobs = []
    selected: dict[str, list[str]] = {}
    for symbol, entry in catalog.items():
        for item in entry["objects"]:
            key = item["key"]
            month = month_from_key(key)
            if not args.start <= month <= args.end:
                continue
            selected.setdefault(symbol, []).append(month)
            kline_path = args.cache / "klines" / symbol / f"{month}.zip"
            jobs.append((f"https://data.binance.vision/{key}", kline_path))
            fund_path = args.cache / "funding" / symbol / f"{month}.zip"
            jobs.append((funding_url(symbol, month), fund_path))

    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_one, url, path): path for url, path in jobs}
        for future in as_completed(futures):
            path, error = future.result()
            if error and error != "404":
                errors[path] = error

    args.output.mkdir(parents=True, exist_ok=True)
    assembled = {}
    for symbol, months in sorted(selected.items()):
        frames = []
        funding_parts = []
        for month in sorted(set(months)):
            kline_path = args.cache / "klines" / symbol / f"{month}.zip"
            if kline_path.exists():
                frames.append(read_daily_klines(kline_path))
            fund_path = args.cache / "funding" / symbol / f"{month}.zip"
            if fund_path.exists():
                funding_parts.append(read_funding(fund_path))
        if not frames:
            continue
        frame = pd.concat(frames).sort_index()
        frame = frame[~frame.index.duplicated(keep="last")]
        if funding_parts:
            rates = pd.concat(funding_parts).groupby(level=0).sum()
            frame["funding"] = rates.reindex(frame.index).fillna(0.0)
        else:
            frame["funding"] = 0.0
        frame.reset_index()[
            ["timestamp", "open", "high", "low", "close", "quote_volume", "funding"]
        ].to_csv(args.output / f"{symbol}.csv", index=False)
        assembled[symbol] = {
            "rows": int(len(frame)),
            "start": str(frame.index.min()),
            "end": str(frame.index.max()),
        }
    summary = {
        "requested_files": len(jobs),
        "non_404_errors": errors,
        "assembled_symbols": len(assembled),
        "symbols": assembled,
    }
    (args.output / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"requested_files": len(jobs), "errors": len(errors), "assembled_symbols": len(assembled)}, indent=2))


if __name__ == "__main__":
    main()
