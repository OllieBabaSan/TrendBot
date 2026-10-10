from __future__ import annotations

import argparse
import json
import urllib.error
from datetime import date
from pathlib import Path

import pandas as pd

from trendbot.binance_archive import ArchiveRequest, download, read_daily_klines, read_funding


def months(start: str, end: str):
    cursor = pd.Period(start, freq="M")
    finish = pd.Period(end, freq="M")
    while cursor <= finish:
        yield cursor.year, cursor.month
        cursor += 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--start", required=True, help="YYYY-MM")
    parser.add_argument("--end", default=date.today().strftime("%Y-%m"))
    parser.add_argument("--cache", type=Path, default=Path("data/archive"))
    parser.add_argument("--output", type=Path, default=Path("data/csv"))
    args = parser.parse_args()

    manifest: dict[str, dict] = {}
    for symbol in [item.upper() for item in args.symbols]:
        kline_frames = []
        funding_parts = []
        missing = []
        for year, month in months(args.start, args.end):
            request = ArchiveRequest(symbol, year, month)
            kline_zip = args.cache / "klines" / symbol / f"{request.month_key}.zip"
            funding_zip = args.cache / "funding" / symbol / f"{request.month_key}.zip"
            try:
                if not kline_zip.exists():
                    download(request.kline_url(), kline_zip)
                kline_frames.append(read_daily_klines(kline_zip))
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                missing.append(request.month_key)
                continue
            try:
                if not funding_zip.exists():
                    download(request.funding_url(), funding_zip)
                funding_parts.append(read_funding(funding_zip))
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise

        if not kline_frames:
            manifest[symbol] = {"status": "no-data", "missing_months": missing}
            continue
        frame = pd.concat(kline_frames).sort_index()
        frame = frame[~frame.index.duplicated(keep="last")]
        if funding_parts:
            rates = pd.concat(funding_parts).groupby(level=0).sum()
            frame["funding"] = rates.reindex(frame.index).fillna(0.0)
        else:
            frame["funding"] = 0.0
        args.output.mkdir(parents=True, exist_ok=True)
        output = args.output / f"{symbol}.csv"
        frame.reset_index()[
            ["timestamp", "open", "high", "low", "close", "quote_volume", "funding"]
        ].to_csv(output, index=False)
        manifest[symbol] = {
            "status": "ok",
            "rows": int(len(frame)),
            "start": str(frame.index.min()),
            "end": str(frame.index.max()),
            "missing_months": missing,
        }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

