from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from trendbot.backtest import _target_weights
from trendbot.binance_archive import point_in_time_eligibility
from trendbot.config import TrendConfig
from trendbot.data import load_csv_panels
from trendbot.hyperliquid_archive import fetch_funding_window, utc_now_iso


def request_windows(dates: pd.DatetimeIndex, max_calendar_days: int = 20) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    remaining = pd.DatetimeIndex(dates).normalize().unique().sort_values()
    windows = []
    cursor = 0
    while cursor < len(remaining):
        start = remaining[cursor]
        end = start + pd.Timedelta(days=max_calendar_days) - pd.Timedelta(milliseconds=1)
        windows.append((start, end))
        cursor += 1
        while cursor < len(remaining) and remaining[cursor] <= end:
            cursor += 1
    return windows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--pause", type=float, default=2.4)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    panels = load_csv_panels(args.data)
    candle_manifest_path = args.data / "manifest.json"
    candle_manifest = json.loads(candle_manifest_path.read_text(encoding="utf-8"))
    api_names = {
        Path(item["file"]).stem.upper(): item.get("name", name)
        for name, item in candle_manifest.get("markets", {}).items()
        if item.get("status") == "ok" and item.get("file")
    }
    eligible = point_in_time_eligibility(panels["quote_volume"], panels["close"])
    targets, _ = _target_weights(panels["close"], TrendConfig(), eligible)
    required = targets.ne(0.0)
    required.iloc[-1] = False  # The simulator has no forward holding period here.
    plan = {}
    for symbol in required.columns[required.any(axis=0)]:
        dates = required.index[required[symbol]]
        windows = request_windows(dates)
        plan[symbol] = {
            "required_days": int(len(pd.DatetimeIndex(dates).normalize().unique())),
            "windows": [(start.isoformat(), end.isoformat()) for start, end in windows],
        }
    total_windows = sum(len(item["windows"]) for item in plan.values())
    if args.plan:
        print(json.dumps({
            "symbols": len(plan),
            "required_market_days": sum(item["required_days"] for item in plan.values()),
            "requests": total_windows,
            "estimated_minutes_at_pause": total_windows * args.pause / 60,
        }, indent=2))
        return
    state = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest.exists() else {
        "source": "Hyperliquid fundingHistory public API",
        "started": utc_now_iso(),
        "symbols": {},
    }
    processed = 0
    for number, (symbol, item) in enumerate(plan.items(), start=1):
        if args.limit is not None and processed >= args.limit:
            break
        symbol_state = state["symbols"].setdefault(symbol, {
            "required_days": item["required_days"], "completed_windows": {},
        })
        api_name = api_names.get(symbol, symbol)
        symbol_state["api_name"] = api_name
        csv_path = args.data / f"{symbol}.csv"
        frame = pd.read_csv(csv_path)
        index = pd.to_datetime(frame["timestamp"], utc=True)
        funding = pd.Series(pd.to_numeric(frame.get("funding", 0.0), errors="coerce").fillna(0.0).to_numpy(), index=index)
        required_dates = required.index[required[symbol]].normalize().unique()
        counts_by_day = {}
        for start_text, end_text in item["windows"]:
            key = start_text[:10]
            prior = symbol_state["completed_windows"].get(key)
            if prior and prior.get("complete"):
                continue
            start, end = pd.Timestamp(start_text), pd.Timestamp(end_text)
            print(f"[{number}/{len(plan)}] {symbol} {start.date()}..{end.date()}", flush=True)
            daily, counts = fetch_funding_window(
                api_name, int(start.timestamp() * 1000), int(end.timestamp() * 1000)
            )
            funding.loc[funding.index.normalize().isin(daily.index)] = daily.reindex(
                funding.index[funding.index.normalize().isin(daily.index)].normalize()
            ).to_numpy()
            window_required = pd.DatetimeIndex(required_dates)[
                (pd.DatetimeIndex(required_dates) >= start.normalize())
                & (pd.DatetimeIndex(required_dates) <= end.normalize())
            ]
            missing = [date.isoformat() for date in window_required if int(counts.get(date, 0)) == 0]
            partial = {
                date.isoformat(): int(counts.get(date, 0))
                for date in window_required if 0 < int(counts.get(date, 0)) < 24
            }
            complete = not missing and not partial
            symbol_state["completed_windows"][key] = {
                "start": start_text, "end": end_text, "records": int(counts.sum()),
                "missing_required_days": missing, "partial_required_days": partial,
                "complete": complete,
            }
            counts_by_day.update({date.isoformat(): int(value) for date, value in counts.items()})
            state["updated"] = utc_now_iso()
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(json.dumps(state, indent=2), encoding="utf-8")
            if args.pause:
                time.sleep(args.pause)
        frame["funding"] = funding.reindex(index).to_numpy()
        frame.to_csv(csv_path, index=False)
        windows = symbol_state["completed_windows"].values()
        symbol_state["complete"] = len(windows) == len(item["windows"]) and all(window.get("complete") for window in windows)
        processed += 1
        args.manifest.write_text(json.dumps(state, indent=2), encoding="utf-8")
    state["updated"] = utc_now_iso()
    state["complete_symbols"] = sum(bool(item.get("complete")) for item in state["symbols"].values())
    state["planned_symbols"] = len(plan)
    args.manifest.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps({
        "planned_symbols": len(plan), "processed_this_run": processed,
        "complete_symbols": state["complete_symbols"], "manifest": str(args.manifest),
    }, indent=2))


if __name__ == "__main__":
    main()
