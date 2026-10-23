from __future__ import annotations

import json
import re
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


INFO_URL = "https://api.hyperliquid.xyz/info"


def post_info(payload: dict, timeout: int = 60, retries: int = 5) -> object:
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            INFO_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "TrendBot-research/0.1"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            if not retryable or attempt == retries:
                raise
            time.sleep(min(60.0, 2.0 ** attempt))
    raise RuntimeError("unreachable retry state")


def safe_symbol(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_").upper()


def parse_candles(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["open", "high", "low", "close", "quote_volume"])
    frame = pd.DataFrame(records)
    index = pd.to_datetime(pd.to_numeric(frame["t"]), unit="ms", utc=True)
    output = pd.DataFrame(index=index)
    for source, target in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close")):
        output[target] = pd.to_numeric(frame[source], errors="coerce").to_numpy()
    base_volume = pd.to_numeric(frame["v"], errors="coerce").to_numpy()
    typical = output[["open", "high", "low", "close"]].mean(axis=1)
    output["quote_volume"] = base_volume * typical
    return output[~output.index.duplicated(keep="last")].sort_index()


def parse_funding(records: list[dict]) -> pd.Series:
    if not records:
        return pd.Series(dtype=float)
    frame = pd.DataFrame(records)
    index = pd.to_datetime(pd.to_numeric(frame["time"]), unit="ms", utc=True)
    rates = pd.to_numeric(frame["fundingRate"], errors="coerce")
    series = pd.Series(rates.to_numpy(), index=index).dropna()
    return series.groupby(series.index.floor("D")).sum().sort_index()


@dataclass(frozen=True)
class HyperliquidMarket:
    name: str
    sz_decimals: int
    max_leverage: int
    is_delisted: bool


def fetch_markets() -> tuple[list[HyperliquidMarket], list[dict]]:
    response = post_info({"type": "metaAndAssetCtxs"})
    metadata, contexts = response
    markets = [
        HyperliquidMarket(
            name=item["name"],
            sz_decimals=int(item["szDecimals"]),
            max_leverage=int(item["maxLeverage"]),
            is_delisted=bool(item.get("isDelisted", False)),
        )
        for item in metadata["universe"]
    ]
    return markets, contexts


def fetch_daily_candles(coin: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    records = post_info({
        "type": "candleSnapshot",
        "req": {"coin": coin, "interval": "1d", "startTime": start_ms, "endTime": end_ms},
    })
    return parse_candles(records)


def fetch_funding_history(coin: str, start_ms: int, end_ms: int, pause: float = 0.0) -> pd.Series:
    records: list[dict] = []
    cursor = start_ms
    while cursor <= end_ms:
        page = post_info({"type": "fundingHistory", "coin": coin, "startTime": cursor, "endTime": end_ms})
        if not page:
            break
        records.extend(page)
        last = int(page[-1]["time"])
        if last < cursor or len(page) < 500:
            break
        cursor = last + 1
        if pause:
            time.sleep(pause)
    return parse_funding(records)


def fetch_funding_window(
    coin: str, start_ms: int, end_ms: int
) -> tuple[pd.Series, pd.Series]:
    records = post_info({
        "type": "fundingHistory", "coin": coin, "startTime": start_ms, "endTime": end_ms
    })
    daily = parse_funding(records)
    if not records:
        return daily, pd.Series(dtype=int)
    timestamps = pd.to_datetime(
        [int(record["time"]) for record in records], unit="ms", utc=True
    )
    counts = pd.Series(1, index=timestamps).groupby(timestamps.floor("D")).sum().astype(int)
    return daily, counts


def write_market_csv(path: Path, candles: pd.DataFrame, funding: pd.Series | None = None) -> None:
    frame = candles.copy()
    frame["funding"] = 0.0 if funding is None else funding.reindex(frame.index).fillna(0.0)
    frame.index.name = "timestamp"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.reset_index()[
        ["timestamp", "open", "high", "low", "close", "quote_volume", "funding"]
    ].to_csv(path, index=False)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
