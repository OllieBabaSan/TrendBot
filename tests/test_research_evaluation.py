import unittest

import numpy as np
import pandas as pd

from trendbot.backtest import BacktestResult
from trendbot.research_evaluation import (
    ChronologicalPartitions,
    ChronologicalSplit,
    contribution_report,
    metrics_for_returns,
    partition_report,
)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.index = pd.date_range("2020-01-01", periods=1000, freq="D", tz="UTC")

    def test_compatibility_splits_are_disjoint_and_complete(self):
        index = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
        masks = ChronologicalSplit("2024-01-03", "2024-01-07").masks(index)
        total = sum(mask.astype(int) for mask in masks.values())
        self.assertTrue((total == 1).all())
        self.assertEqual(int(masks["design"].sum()), 3)
        self.assertEqual(int(masks["validation"].sum()), 4)
        self.assertEqual(int(masks["test"].sum()), 3)

    def test_four_partitions_are_disjoint_and_complete(self):
        p = ChronologicalPartitions("2020-09-01", "2021-05-01", "2022-01-01")
        masks = p.masks(self.index)
        summed = sum(mask.astype(int) for mask in masks.values())
        self.assertTrue((summed == 1).all())

    def test_invalid_partition_order_rejected(self):
        p = ChronologicalPartitions("2021-01-01", "2020-12-01", "2022-01-01")
        with self.assertRaises(ValueError):
            p.validate(self.index)

    def test_partition_report_does_not_mix_periods(self):
        daily = pd.DataFrame(
            {"net_return": np.where(np.arange(len(self.index)) < 500, 0.001, -0.001)},
            index=self.index,
        )
        result = BacktestResult(
            daily=daily,
            positions=pd.DataFrame(index=self.index),
            metrics={},
            attribution=pd.DataFrame(index=self.index),
        )
        p = ChronologicalPartitions("2020-09-01", "2021-05-01", "2022-01-01")
        report = partition_report(result, p)
        self.assertGreater(report["design"]["total_return"], 0)
        self.assertLess(report["final_test"]["total_return"], 0)

    def test_contribution_detects_dominant_market(self):
        idx = pd.date_range("2024-01-01", periods=5, freq="D", tz="UTC")
        opens = pd.DataFrame({"A": [1, 2, 3, 4, 5], "B": [1, 1, 1, 1, 1]}, index=idx)
        positions = pd.DataFrame({"A": [1, 1, 1, 1], "B": [1, 1, 1, 1]}, index=idx[:-1])
        report = contribution_report(positions, opens)
        self.assertGreater(report["top_positive_market_share"], 0.99)

    def test_drawdown_includes_initial_equity(self):
        report = metrics_for_returns(pd.Series([-0.10, 0.05]))
        self.assertAlmostEqual(report["max_drawdown"], -0.10)


if __name__ == "__main__":
    unittest.main()
