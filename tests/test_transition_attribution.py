import pandas as pd

from scripts.analyze_transition_losses import position_ages


def test_position_ages_reset_when_flat_or_direction_changes():
    positions = pd.DataFrame({"x": [1.0, 0.5, 0.0, -0.2, -0.3, 0.4]})
    assert position_ages(positions)["x"].tolist() == [1, 2, 0, 1, 2, 1]
