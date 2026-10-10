from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from .archive_universe import ArchiveMonth, BUCKET_URL


@dataclass(frozen=True)
class DownloadRecord:
    key: str
    status: str
    bytes: int
    sha256: str | None
    error: str | None = None


def local_path(cache: Path, key: str) -> Path:
    return cache.joinpath(*key.split("/"))


def _download_key(key: str, cache: Path, timeout: int) -> DownloadRecord:
    destination = local_path(cache, key)
    if destination.exists():
        data = destination.read_bytes()
        return DownloadRecord(key, "cached", len(data), hashlib.sha256(data).hexdigest())
    url = f"{BUCKET_URL}/{key}"
    request = urllib.request.Request(url, headers={"User-Agent": "TrendBot/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return DownloadRecord(key, "missing", 0, None, "HTTP 404")
        return DownloadRecord(key, "error", 0, None, f"HTTP {exc.code}")
    except OSError as exc:
        return DownloadRecord(key, "error", 0, None, type(exc).__name__)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(data)
    temporary.replace(destination)
    return DownloadRecord(key, "downloaded", len(data), hashlib.sha256(data).hexdigest())


def download_months(
    months: tuple[ArchiveMonth, ...],
    cache: Path,
    ledger: Path,
    include_funding: bool = True,
    timeout: int = 60,
) -> list[DownloadRecord]:
    records: list[DownloadRecord] = []
    for month in months:
        records.append(_download_key(month.kline_key, cache, timeout))
        if include_funding:
            records.append(_download_key(month.funding_key, cache, timeout))
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
    return records

