from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from trendbot.hyperliquid_archive import (
    fetch_daily_candles,
    fetch_funding_history,
    fetch_markets,
    safe_symbol,
    utc_now_iso,
    write_market_csv,
)


def epoch_ms(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp() * 1000)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/hyperliquid-csv"))
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--end", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--symbols", nargs="*")
    parser.add_argument("--pause", type=float, default=2.0)
    parser.add_argument("--funding", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    start_ms, end_ms = epoch_ms(args.start), epoch_ms(args.end) + 86_399_999
    markets, contexts = fetch_markets()
    requested = {item.upper() for item in args.symbols} if args.symbols else None
    selected = [market for market in markets if requested is None or market.name.upper() in requested]
    context_by_name = {market.name: contexts[i] for i, market in enumerate(markets)}
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if args.resume and manifest_path.exists() else {
        "source": "Hyperliquid public info API",
        "api": "https://api.hyperliquid.xyz/info",
        "snapshot_started": utc_now_iso(),
        "requested_start": args.start,
        "requested_end": args.end,
        "funding_requested": args.funding,
        "markets": {},
    }
    for number, market in enumerate(selected, start=1):
        slug = safe_symbol(market.name)
        output = args.output / f"{slug}.csv"
        prior = manifest["markets"].get(market.name, {})
        if args.resume and output.exists() and prior.get("status") == "ok" and (not args.funding or prior.get("funding_complete")):
            print(f"[{number}/{len(selected)}] skip {market.name}", flush=True)
            continue
        try:
            print(f"[{number}/{len(selected)}] candles {market.name}", flush=True)
            candles = fetch_daily_candles(market.name, start_ms, end_ms)
            funding = None
            funding_complete = False
            if args.funding and not candles.empty:
                print(f"[{number}/{len(selected)}] funding {market.name}", flush=True)
                first_ms = int(candles.index.min().timestamp() * 1000)
                funding = fetch_funding_history(market.name, first_ms, end_ms, pause=args.pause)
                funding_complete = True
            if candles.empty:
                item = {"status": "no-data"}
            else:
                write_market_csv(output, candles, funding)
                item = {
                    "status": "ok",
                    "file": output.name,
                    "rows": len(candles),
                    "start": str(candles.index.min()),
                    "end": str(candles.index.max()),
                    "funding_complete": funding_complete,
                    "funding_days": 0 if funding is None else len(funding),
                }
            item.update({
                "name": market.name,
                "sz_decimals": market.sz_decimals,
                "max_leverage": market.max_leverage,
                "is_delisted": market.is_delisted,
                "current_context": context_by_name.get(market.name),
            })
            manifest["markets"][market.name] = item
        except Exception as error:
            manifest["markets"][market.name] = {"status": "error", "error": repr(error)}
        manifest["snapshot_updated"] = utc_now_iso()
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        if args.pause:
            time.sleep(args.pause)
    manifest["snapshot_completed"] = utc_now_iso()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    counts = {}
    for item in manifest["markets"].values():
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print(json.dumps({"selected": len(selected), "counts": counts, "manifest": str(manifest_path)}, indent=2))


if __name__ == "__main__":
    main()
