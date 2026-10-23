import unittest

import numpy as np
import pandas as pd

from trendbot.backtest import forward_mark_returns, run_backtest
from trendbot.config import TrendConfig


class BacktestTests(unittest.TestCase):
    def setUp(self):
        self.index = pd.date_range("2018-01-01", periods=1100, freq="D", tz="UTC")
        cycle = 0.02 * np.sin(np.arange(len(self.index)) / 11)
        btc = np.exp(np.linspace(4, 7, len(self.index)) + cycle)
        eth = np.exp(np.linspace(3, 5.4, len(self.index)) - cycle)
        self.open = pd.DataFrame({"BTC": btc, "ETH": eth}, index=self.index)
        self.close = self.open * (1 + 0.001 * np.sin(np.arange(len(self.index)) / 3)[:, None])

    def test_backtest_is_deterministic_and_finite(self):
        config = TrendConfig(cost_bps=10)
        one = run_backtest(self.open, self.close, config)
        two = run_backtest(self.open, self.close, config)
        self.assertEqual(one.metrics, two.metrics)
        self.assertTrue(np.isfinite(one.daily.to_numpy()).all())

    def test_costs_reduce_equity(self):
        free = run_backtest(self.open, self.close, TrendConfig(cost_bps=0))
        costly = run_backtest(self.open, self.close, TrendConfig(cost_bps=20))
        self.assertGreater(free.daily["equity"].iloc[-1], costly.daily["equity"].iloc[-1])

    def test_gross_cap_holds(self):
        result = run_backtest(
            self.open,
            self.close,
            TrendConfig(target_vol_annual=1.0, max_gross_leverage=1.25),
        )
        self.assertLessEqual(float(result.daily["gross_exposure"].max()), 1.2500001)

    def test_held_book_cap_survives_buffering(self):
        result = run_backtest(
            self.open,
            self.close,
            TrendConfig(
                target_vol_annual=2.0,
                max_gross_leverage=0.30,
                rebalance_buffer=0.40,
            ),
        )
        self.assertLessEqual(float(result.daily["gross_exposure"].max()), 0.3000001)

    def test_disappearing_market_is_marked_to_final_close(self):
        index = pd.date_range("2018-01-01", periods=1100, freq="D", tz="UTC")
        open_frame = self.open.copy()
        close_frame = self.close.copy()
        open_frame.loc[index[-2]:, "ETH"] = np.nan
        close_frame.loc[index[-1]:, "ETH"] = np.nan
        result = run_backtest(open_frame, close_frame, TrendConfig(cost_bps=10))
        self.assertTrue(np.isfinite(result.daily.to_numpy()).all())
        self.assertEqual(float(result.positions["ETH"].iloc[-1]), 0.0)

    def test_temporary_missing_open_carries_gap_return(self):
        index = pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC")
        opens = pd.DataFrame({"X": [100.0, np.nan, 120.0, 126.0]}, index=index)
        closes = pd.DataFrame({"X": [105.0, np.nan, 123.0, 126.0]}, index=index)
        forward, terminal = forward_mark_returns(opens, closes)
        self.assertAlmostEqual(float(forward.iloc[0, 0]), 0.05)
        self.assertAlmostEqual(float(forward.iloc[1, 0]), 120.0 / 105.0 - 1.0)
        self.assertFalse(bool(terminal.iloc[0, 0]))

    def test_final_observation_is_the_only_terminal_mark(self):
        index = pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC")
        opens = pd.DataFrame({"X": [100.0, 110.0, np.nan, np.nan]}, index=index)
        closes = pd.DataFrame({"X": [105.0, 108.0, np.nan, np.nan]}, index=index)
        _, terminal = forward_mark_returns(opens, closes)
        self.assertFalse(bool(terminal.iloc[0, 0]))
        self.assertTrue(bool(terminal.iloc[1, 0]))


if __name__ == "__main__":
    unittest.main()
