import unittest

import numpy as np
import pandas as pd

from trendbot.backtest import run_backtest
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


if __name__ == "__main__":
    unittest.main()

