import unittest

import numpy as np

from trendbot.hyperliquid_archive import parse_candles, parse_funding, safe_symbol


class HyperliquidArchiveTests(unittest.TestCase):
    def test_candles_compute_quote_volume_without_lookahead(self):
        frame = parse_candles([{
            "t": 1_700_000_000_000, "o": "10", "h": "12", "l": "8", "c": "10", "v": "5"
        }])
        self.assertEqual(float(frame.iloc[0]["open"]), 10.0)
        self.assertEqual(float(frame.iloc[0]["quote_volume"]), 50.0)

    def test_hourly_funding_is_summed_by_utc_day(self):
        rates = parse_funding([
            {"time": 1_704_067_200_000, "fundingRate": "0.001"},
            {"time": 1_704_070_800_000, "fundingRate": "-0.00025"},
        ])
        self.assertEqual(len(rates), 1)
        self.assertTrue(np.isclose(float(rates.iloc[0]), 0.00075))

    def test_symbol_is_windows_safe(self):
        self.assertEqual(safe_symbol("xyz:ABC/USDC"), "XYZ_ABC_USDC")
