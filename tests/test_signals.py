import unittest
from dataclasses import replace

import numpy as np
import pandas as pd

from trendbot.config import TrendConfig
from trendbot.signals import annualized_volatility, response, trend_signal


class SignalTests(unittest.TestCase):
    def test_signal_is_causal(self):
        index = pd.date_range("2020-01-01", periods=700, freq="D", tz="UTC")
        base = pd.DataFrame({"BTC": np.exp(np.linspace(4, 6, len(index)))}, index=index)
        changed = base.copy()
        changed.iloc[-1, 0] *= 10
        first = trend_signal(base, TrendConfig())
        second = trend_signal(changed, TrendConfig())
        pd.testing.assert_series_equal(first.iloc[-1], second.iloc[-1])

    def test_uptrend_eventually_produces_positive_signal(self):
        index = pd.date_range("2020-01-01", periods=700, freq="D", tz="UTC")
        noise = 0.01 * np.sin(np.arange(len(index)) / 7)
        close = pd.DataFrame({"BTC": np.exp(np.linspace(4, 6, len(index)) + noise)}, index=index)
        signal = trend_signal(close, TrendConfig())
        self.assertGreater(float(signal["BTC"].dropna().iloc[-1]), 0)

    def test_position_modes(self):
        values = pd.DataFrame({"A": [-2.0, 2.0]})
        long_only = response(values, TrendConfig(position_mode="long_only"))
        short_only = response(values, TrendConfig(position_mode="short_only"))
        self.assertEqual(float(long_only.iloc[0, 0]), 0.0)
        self.assertGreater(float(long_only.iloc[1, 0]), 0.0)
        self.assertLess(float(short_only.iloc[0, 0]), 0.0)
        self.assertEqual(float(short_only.iloc[1, 0]), 0.0)

    def test_fast_horizon_can_trade_before_slowest_is_ready(self):
        index = pd.date_range("2020-01-01", periods=170, freq="D", tz="UTC")
        wave = 0.02 * np.sin(np.arange(len(index)) / 5)
        close = pd.DataFrame(
            {"YOUNG": np.exp(np.linspace(4, 5, len(index)) + wave)}, index=index
        )
        signal = trend_signal(close, TrendConfig())
        self.assertTrue(signal["YOUNG"].iloc[120:170].notna().any())

    def test_blended_volatility_lies_between_short_and_long_forecasts(self):
        index = pd.date_range("2020-01-01", periods=500, freq="D", tz="UTC")
        returns = np.r_[np.full(250, 0.002), np.tile([0.05, -0.04], 125)]
        close = pd.DataFrame({"X": 100 * np.exp(np.cumsum(returns))}, index=index)
        base = TrendConfig(vol_short_min_periods=20, vol_long_min_periods=60)
        short = annualized_volatility(close, replace(base, vol_forecast="short"))
        long = annualized_volatility(close, replace(base, vol_forecast="long"))
        blend = annualized_volatility(
            close, replace(base, vol_forecast="blend", vol_blend_short=0.5)
        )
        low = min(float(short.iloc[-1, 0]), float(long.iloc[-1, 0]))
        high = max(float(short.iloc[-1, 0]), float(long.iloc[-1, 0]))
        self.assertGreaterEqual(float(blend.iloc[-1, 0]), low)
        self.assertLessEqual(float(blend.iloc[-1, 0]), high)


if __name__ == "__main__":
    unittest.main()
