from __future__ import annotations

import numpy as np
import pandas as pd

from .config import TrendConfig


def annualized_volatility(close: pd.DataFrame, config: TrendConfig) -> pd.DataFrame:
    """Volatility known at the current close; callers lag before execution."""
    log_return = np.log(close).diff()
    short = log_return.rolling(
        config.vol_window, min_periods=config.vol_short_min_periods
    ).std()
    long = log_return.rolling(
        config.vol_long_window, min_periods=config.vol_long_min_periods
    ).std()
    ewma = log_return.ewm(
        span=config.vol_window, min_periods=config.vol_short_min_periods, adjust=False
    ).std()
    if config.vol_forecast == "long":
        daily = long.where(long.notna(), short)
    elif config.vol_forecast == "blend":
        daily = config.vol_blend_short * short + (1 - config.vol_blend_short) * long
        daily = daily.where(long.notna(), short)
    elif config.vol_forecast == "ewma":
        daily = ewma
    else:
        daily = short
    annual = daily * np.sqrt(config.annualization_days)
    return annual.clip(lower=config.vol_floor_annual)


def trend_signal(close: pd.DataFrame, config: TrendConfig) -> pd.DataFrame:
    """Return a signal at row t using closes no later than t-1."""
    config.validate()
    log_price = np.log(close)
    daily_vol = annualized_volatility(close, config) / np.sqrt(config.annualization_days)
    components: list[pd.DataFrame] = []
    for fast, slow in config.speeds:
        raw = (
            log_price.ewm(span=fast, min_periods=fast, adjust=False).mean()
            - log_price.ewm(span=slow, min_periods=slow, adjust=False).mean()
        )
        normalized = raw / (daily_vol * np.sqrt(slow))
        scale = normalized.rolling(
            config.signal_scale_window,
            min_periods=config.signal_scale_min_periods,
        ).std()
        components.append(normalized / scale.replace(0.0, np.nan))
    # Average whichever horizons are presently available. Requiring the
    # slowest component would impose an unintended 192-day listing-age gate
    # and contradict the reference design's young-market behavior.
    stacked = pd.concat(components, axis=0, keys=range(len(components)))
    combined = stacked.groupby(level=1).mean().reindex(close.index)
    return combined.shift(1)


def response(signal: pd.DataFrame, config: TrendConfig) -> pd.DataFrame:
    if config.response_kind == "tanh":
        value = np.tanh(signal)
    elif config.response_kind == "binary":
        value = np.sign(signal)
    else:
        value = signal.clip(-1.0, 1.0)
    if config.position_mode == "long_only":
        return value.clip(lower=0.0)
    if config.position_mode == "short_only":
        return value.clip(upper=0.0)
    return value
