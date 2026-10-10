from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_csv_directory(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    panels = load_csv_panels(path)
    return panels["open"], panels["close"], panels["funding"]


def load_csv_panels(path: Path) -> dict[str, pd.DataFrame]:
    opens: dict[str, pd.Series] = {}
    closes: dict[str, pd.Series] = {}
    funding: dict[str, pd.Series] = {}
    quote_volume: dict[str, pd.Series] = {}
    for csv_path in sorted(path.glob("*.csv")):
        frame = pd.read_csv(csv_path)
        required = {"timestamp", "open", "close"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{csv_path.name} missing columns: {sorted(missing)}")
        index = pd.to_datetime(frame["timestamp"], utc=True)
        symbol = csv_path.stem.upper()
        opens[symbol] = pd.Series(frame["open"].to_numpy(float), index=index)
        closes[symbol] = pd.Series(frame["close"].to_numpy(float), index=index)
        if "funding" in frame:
            funding[symbol] = pd.Series(frame["funding"].to_numpy(float), index=index)
        if "quote_volume" in frame:
            quote_volume[symbol] = pd.Series(
                frame["quote_volume"].to_numpy(float), index=index
            )
    if not opens:
        raise ValueError(f"no CSV files found in {path}")
    open_frame = pd.DataFrame(opens).sort_index()
    close_frame = pd.DataFrame(closes).sort_index()
    funding_frame = pd.DataFrame(funding, index=open_frame.index).fillna(0.0)
    volume_frame = pd.DataFrame(quote_volume, index=open_frame.index)
    return {
        "open": open_frame,
        "close": close_frame,
        "funding": funding_frame,
        "quote_volume": volume_frame,
    }
