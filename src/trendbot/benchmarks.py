from __future__ import annotations

import numpy as np
import pandas as pd


def cash_returns(index: pd.DatetimeIndex) -> pd.Series:
    return pd.Series(0.0, index=index, name="cash")


def equal_weight_buy_hold(opens: pd.DataFrame) -> pd.Series:
    return (opens.shift(-1) / opens - 1.0).mean(axis=1).iloc[:-1].rename("equal_weight_buy_hold")


def moving_average_timing(
    opens: pd.DataFrame, closes: pd.DataFrame, window: int = 200
) -> pd.Series:
    state = (closes > closes.rolling(window, min_periods=window).mean()).shift(1)
    forward = opens.shift(-1) / opens - 1.0
    return (state.astype(float) * forward).mean(axis=1).iloc[:-1].rename("ma_timing")


def benchmark_report(opens: pd.DataFrame, closes: pd.DataFrame) -> dict[str, pd.Series]:
    index = opens.index[:-1]
    return {
        "cash": cash_returns(index),
        "equal_weight_buy_hold": equal_weight_buy_hold(opens).reindex(index),
        "ma_200_timing": moving_average_timing(opens, closes, 200).reindex(index),
    }

