import unittest

import pandas as pd

from trendbot.evaluation import ChronologicalSplit


class EvaluationTests(unittest.TestCase):
    def test_splits_are_disjoint_and_complete(self):
        index = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
        masks = ChronologicalSplit("2024-01-03", "2024-01-07").masks(index)
        total = sum(mask.astype(int) for mask in masks.values())
        self.assertTrue((total == 1).all())
        self.assertEqual(int(masks["design"].sum()), 3)
        self.assertEqual(int(masks["validation"].sum()), 4)
        self.assertEqual(int(masks["test"].sum()), 3)


if __name__ == "__main__":
    unittest.main()
