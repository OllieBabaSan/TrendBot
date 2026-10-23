import pandas as pd

from scripts.run_speed_sleeve_experiment import combine_equal_sleeves


def test_combined_sleeves_respect_shared_gross_cap():
    first = pd.DataFrame({"a": [2.0], "b": [1.0]})
    second = pd.DataFrame({"a": [1.0], "b": [-2.0]})
    combined = combine_equal_sleeves([first, second], 1.5)
    assert combined.abs().sum(axis=1).iloc[0] <= 1.5 + 1e-12
