from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path


BUCKET_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DAILY_PREFIX = "data/futures/um/monthly/klines/"
_DAILY_KEY = re.compile(
    r"^data/futures/um/monthly/klines/(?P<symbol>[A-Z0-9_]+)/1d/"
    r"(?P=symbol)-1d-(?P<year>\d{4})-(?P<month>\d{2})\.zip$"
)


@dataclass(frozen=True, order=True)
class ArchiveMonth:
    symbol: str
    year: int
    month: int
    kline_key: str

    @property
    def month_key(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def funding_key(self) -> str:
        name = f"{self.symbol}-fundingRate-{self.month_key}.zip"
        return f"data/futures/um/monthly/fundingRate/{self.symbol}/{name}"

    def in_range(self, start: date, end: date) -> bool:
        current = date(self.year, self.month, 1)
        return date(start.year, start.month, 1) <= current <= date(end.year, end.month, 1)


@dataclass(frozen=True)
class ArchiveCatalog:
    source: str
    generated_from_keys: int
    months: tuple[ArchiveMonth, ...]

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(sorted({entry.symbol for entry in self.months}))

    def select(self, start: date, end: date) -> tuple[ArchiveMonth, ...]:
        if end < start:
            raise ValueError("end must not precede start")
        return tuple(entry for entry in self.months if entry.in_range(start, end))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source": self.source,
            "generated_from_keys": self.generated_from_keys,
            "symbols": list(self.symbols),
            "months": [asdict(entry) for entry in self.months],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> "ArchiveCatalog":
        payload = json.loads(path.read_text(encoding="utf-8"))
        months = tuple(ArchiveMonth(**row) for row in payload["months"])
        return cls(
            source=payload["source"],
            generated_from_keys=int(payload["generated_from_keys"]),
            months=months,
        )


def parse_listing_page(xml: bytes) -> tuple[list[str], str | None]:
    root = ET.fromstring(xml)
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}", 1)[0] + "}"
    keys = [node.text or "" for node in root.findall(f"{namespace}Contents/{namespace}Key")]
    truncated = (root.findtext(f"{namespace}IsTruncated") or "false").lower() == "true"
    token = root.findtext(f"{namespace}NextContinuationToken") if truncated else None
    if truncated and not token:
        raise ValueError("truncated archive listing omitted continuation token")
    return keys, token


def parse_prefix_page(xml: bytes) -> tuple[list[str], str | None]:
    root = ET.fromstring(xml)
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}", 1)[0] + "}"
    prefixes = [
        node.text or ""
        for node in root.findall(f"{namespace}CommonPrefixes/{namespace}Prefix")
    ]
    truncated = (root.findtext(f"{namespace}IsTruncated") or "false").lower() == "true"
    token = root.findtext(f"{namespace}NextContinuationToken") if truncated else None
    if truncated and not token:
        raise ValueError("truncated archive prefix listing omitted continuation token")
    return prefixes, token


def _fetch_pages(prefix: str, timeout: int, delimiter: str | None = None) -> list[str]:
    values: list[str] = []
    token: str | None = None
    while True:
        query = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if delimiter:
            query["delimiter"] = delimiter
        if token:
            query["continuation-token"] = token
        url = f"{BUCKET_URL}?{urllib.parse.urlencode(query)}"
        request = urllib.request.Request(url, headers={"User-Agent": "TrendBot/0.1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
        page, token = (
            parse_prefix_page(payload) if delimiter else parse_listing_page(payload)
        )
        values.extend(page)
        if token is None:
            return values


def fetch_daily_archive_keys(timeout: int = 60, workers: int = 16) -> list[str]:
    """Discover daily archives without scanning every intraday timeframe."""
    symbol_prefixes = _fetch_pages(DAILY_PREFIX, timeout, delimiter="/")

    def daily_keys(symbol_prefix: str) -> list[str]:
        return _fetch_pages(f"{symbol_prefix}1d/", timeout)

    keys: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for page in executor.map(daily_keys, symbol_prefixes):
            keys.extend(page)
    return sorted(keys)


def catalog_from_keys(keys: list[str]) -> ArchiveCatalog:
    entries: dict[tuple[str, int, int], ArchiveMonth] = {}
    for key in keys:
        match = _DAILY_KEY.match(key)
        if not match:
            continue
        symbol = match.group("symbol")
        year = int(match.group("year"))
        month = int(match.group("month"))
        if not 1 <= month <= 12:
            continue
        identity = (symbol, year, month)
        entry = ArchiveMonth(symbol=symbol, year=year, month=month, kline_key=key)
        if identity in entries and entries[identity] != entry:
            raise ValueError(f"conflicting archive keys for {identity}")
        entries[identity] = entry
    return ArchiveCatalog(
        source=BUCKET_URL,
        generated_from_keys=len(keys),
        months=tuple(sorted(entries.values())),
    )


def discover_catalog(path: Path, timeout: int = 60) -> ArchiveCatalog:
    keys = fetch_daily_archive_keys(timeout=timeout)
    catalog = catalog_from_keys(keys)
    catalog.write(path)
    return catalog
