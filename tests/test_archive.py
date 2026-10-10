import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

from trendbot.binance_archive import (
    point_in_time_eligibility,
    read_daily_klines,
    read_funding,
)


def write_zip(path: Path, name: str, rows: list[list[object]]) -> None:
    stream = io.StringIO()
    csv.writer(stream, lineterminator="\n").writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(name, stream.getvalue())


class ArchiveTests(unittest.TestCase):
    def test_kline_and_funding_parsers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kline = root / "k.zip"
            funding = root / "f.zip"
            write_zip(kline, "k.csv", [[0, 100, 101, 99, 100.5, 5, 1, 500, 3, 2, 200, 0]])
            write_zip(funding, "f.csv", [["calc_time", "funding_interval_hours", "last_funding_rate"], [0, 8, "0.0001"], [28_800_000, 8, "-0.00004"]])
            self.assertEqual(float(read_daily_klines(kline)["close"].iloc[0]), 100.5)
            self.assertAlmostEqual(float(read_funding(funding).iloc[0]), 0.00006)

    def test_eligibility_has_no_current_day_volume(self):
        index = pd.date_range("2024-01-01", periods=6, freq="D", tz="UTC")
        close = pd.DataFrame({"A": range(1, 7)}, index=index, dtype=float)
        volume = pd.DataFrame({"A": [10, 10, 10, 10, 10, 1_000_000]}, index=index, dtype=float)
        eligible = point_in_time_eligibility(
            volume, close, min_history_days=2, volume_window=2, minimum_median_quote_volume=100
        )
        self.assertFalse(bool(eligible.iloc[-1, 0]))


if __name__ == "__main__":
    unittest.main()

