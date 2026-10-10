from __future__ import annotations

import csv
import io
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ARCHIVE_ROOT = "https://data.binance.vision/data/futures/um/monthly"
ARCHIVE_BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
S3_NAMESPACE = "{http://s3.amazonaws.com/doc/2006-03-01/}"


@dataclass(frozen=True)
class ArchiveRequest:
    symbol: str
    year: int
    month: int

    @property
    def month_key(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    def kline_url(self) -> str:
        name = f"{self.symbol.upper()}-1d-{self.month_key}.zip"
        return f"{ARCHIVE_ROOT}/klines/{self.symbol.upper()}/1d/{name}"

    def funding_url(self) -> str:
        name = f"{self.symbol.upper()}-fundingRate-{self.month_key}.zip"
        return f"{ARCHIVE_ROOT}/fundingRate/{self.symbol.upper()}/{name}"


def download(url: str, destination: Path, timeout: int = 60) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    parts = urllib.parse.urlsplit(url)
    safe_url = urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, urllib.parse.quote(parts.path), parts.query, parts.fragment)
    )
    request = urllib.request.Request(safe_url, headers={"User-Agent": "TrendBot/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        destination.write_bytes(response.read())
    return destination


def list_s3(prefix: str, delimiter: str | None = None) -> tuple[list[dict], list[str]]:
    """List every public Binance archive object/prefix with pagination."""
    objects: list[dict] = []
    prefixes: list[str] = []
    token: str | None = None
    while True:
        query = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if delimiter:
            query["delimiter"] = delimiter
        if token:
            query["continuation-token"] = token
        url = ARCHIVE_BUCKET + "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, headers={"User-Agent": "TrendBot/0.1"})
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    root = ET.fromstring(response.read())
                break
            except (OSError, urllib.error.URLError) as error:
                last_error = error
                if attempt == 3:
                    raise
                time.sleep(1.5 * (attempt + 1))
        else:  # pragma: no cover - loop either breaks or raises
            raise RuntimeError("archive listing failed") from last_error
        for content in root.findall(f"{S3_NAMESPACE}Contents"):
            objects.append(
                {
                    "key": content.findtext(f"{S3_NAMESPACE}Key"),
                    "size": int(content.findtext(f"{S3_NAMESPACE}Size") or 0),
                    "last_modified": content.findtext(f"{S3_NAMESPACE}LastModified"),
                }
            )
        prefixes.extend(
            item.findtext(f"{S3_NAMESPACE}Prefix") or ""
            for item in root.findall(f"{S3_NAMESPACE}CommonPrefixes")
        )
        truncated = root.findtext(f"{S3_NAMESPACE}IsTruncated") == "true"
        token = root.findtext(f"{S3_NAMESPACE}NextContinuationToken")
        if not truncated or not token:
            break
    return objects, prefixes


def list_perpetual_symbols(quote: str = "USDT") -> list[str]:
    _, prefixes = list_s3("data/futures/um/monthly/klines/", delimiter="/")
    symbols = [prefix.rstrip("/").split("/")[-1] for prefix in prefixes]
    return sorted(symbol for symbol in symbols if symbol.endswith(quote))


def list_daily_archives(symbol: str) -> list[dict]:
    prefix = f"data/futures/um/monthly/klines/{symbol.upper()}/1d/"
    objects, _ = list_s3(prefix)
    return [item for item in objects if str(item["key"]).endswith(".zip")]


def _read_zip_rows(path: Path) -> list[list[str]]:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected one CSV in {path}, found {len(members)}")
        text = archive.read(members[0]).decode("utf-8")
    return list(csv.reader(io.StringIO(text)))


def read_daily_klines(path: Path) -> pd.DataFrame:
    rows = _read_zip_rows(path)
    if rows and not rows[0][0].lstrip("-").isdigit():
        rows = rows[1:]
    columns = [
        "open_time", "open", "high", "low", "close", "volume", "close_time",
        "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
    ]
    frame = pd.DataFrame(rows, columns=columns[: len(rows[0])])
    for column in ("open", "high", "low", "close", "volume", "quote_volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["timestamp"] = pd.to_datetime(
        pd.to_numeric(frame["open_time"], errors="coerce"), unit="ms", utc=True
    )
    return frame.set_index("timestamp").sort_index()


def read_funding(path: Path) -> pd.Series:
    rows = _read_zip_rows(path)
    header = rows[0]
    if header and not header[0].lstrip("-").isdigit():
        data = rows[1:]
        frame = pd.DataFrame(data, columns=header)
        time_column = next(c for c in frame if "time" in c.lower())
        rate_column = next(c for c in frame if "rate" in c.lower())
    else:
        frame = pd.DataFrame(rows)
        time_column, rate_column = frame.columns[0], frame.columns[-1]
    timestamp = pd.to_datetime(
        pd.to_numeric(frame[time_column], errors="coerce"), unit="ms", utc=True
    )
    rate = pd.to_numeric(frame[rate_column], errors="coerce")
    series = pd.Series(rate.to_numpy(), index=timestamp).dropna()
    return series.groupby(series.index.floor("D")).sum().sort_index()


def point_in_time_eligibility(
    quote_volume: pd.DataFrame,
    closes: pd.DataFrame,
    min_history_days: int = 120,
    volume_window: int = 30,
    minimum_median_quote_volume: float = 5_000_000,
) -> pd.DataFrame:
    """Eligibility uses observations strictly before the execution day."""
    complete = closes.notna()
    history = complete.cumsum().shift(1).fillna(0)
    liquidity = quote_volume.shift(1).rolling(
        volume_window, min_periods=volume_window
    ).median()
    return (
        (history >= min_history_days)
        & (liquidity >= minimum_median_quote_volume)
        & complete.shift(1).fillna(False)
        & complete
    )
