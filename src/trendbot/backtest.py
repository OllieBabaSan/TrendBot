from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import TrendConfig
from .signals import annualized_volatility, response, trend_signal
from .clustering import average_linkage_labels, equal_cluster_risk_multipliers


@dataclass
class BacktestResult:
    daily: pd.DataFrame
    positions: pd.DataFrame
    metrics: dict[str, float]
    attribution: pd.DataFrame


def forward_mark_returns(
    opens: pd.DataFrame, closes: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Open-to-next-mark returns and retrospective terminal settlements.

    Missing opens freeze execution but not economic exposure. A current close
    supplies that day's mark and a later resumed open captures the intervening
    gap. A market is terminal only after its final observable open; using the
    future availability here determines settlement accounting, never a signal.
    """
    open_values = opens.to_numpy(dtype=float)
    close_values = closes.to_numpy(dtype=float)
    returns = np.full_like(open_values, np.nan, dtype=float)
    terminal = np.zeros_like(open_values, dtype=bool)
    mark = np.full(open_values.shape[1], np.nan, dtype=float)
    future_open = np.zeros_like(open_values, dtype=bool)
    seen = np.zeros(open_values.shape[1], dtype=bool)
    for row in range(len(opens) - 1, -1, -1):
        future_open[row] = seen
        seen |= np.isfinite(open_values[row])
    for row in range(len(opens)):
        has_open = np.isfinite(open_values[row])
        mark = np.where(has_open, open_values[row], mark)
        next_open = (
            np.isfinite(open_values[row + 1])
            if row + 1 < len(opens)
            else np.zeros(open_values.shape[1], dtype=bool)
        )
        end_mark = (
            np.where(next_open, open_values[row + 1], mark)
            if row + 1 < len(opens)
            else mark.copy()
        )
        has_close = np.isfinite(close_values[row])
        end_mark = np.where(~next_open & has_close, close_values[row], end_mark)
        with np.errstate(divide="ignore", invalid="ignore"):
            returns[row] = end_mark / mark - 1.0
        terminal[row] = has_open & has_close & ~future_open[row]
        mark = end_mark
    return (
        pd.DataFrame(returns, index=opens.index, columns=opens.columns),
        pd.DataFrame(terminal, index=opens.index, columns=opens.columns),
    )


def _target_weights(
    close: pd.DataFrame,
    config: TrendConfig,
    tradeable: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    signal = trend_signal(close, config)
    # The volatility estimate is lagged independently so a position filled at
    # today's open never uses today's close.
    vol = annualized_volatility(close, config).shift(1)
    raw = response(signal, config) / vol
    raw = raw.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if tradeable is not None:
        raw = raw.where(tradeable.reindex_like(raw).fillna(False), 0.0)

    returns = close.pct_change(fill_method=None)
    targets = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    cached_correlation: np.ndarray | None = None
    cached_columns = np.zeros(0, dtype=int)
    cached_labels: np.ndarray | None = None
    last_rebuild = -10**9
    for i in range(len(close)):
        vector = raw.iloc[i].to_numpy(dtype=float, copy=True)
        active = np.isfinite(vector) & (vector != 0)
        if active.sum() == 0:
            continue
        if i - last_rebuild >= config.correlation_rebuild_days:
            lo = max(0, i - config.correlation_window)
            block = returns.iloc[lo:i]
            observations = block.notna().sum().to_numpy()
            columns = np.flatnonzero(active & (observations >= config.correlation_min_observations))
            if len(columns) >= 2:
                correlation = block.iloc[:, columns].corr(min_periods=config.correlation_min_observations)
                array = correlation.to_numpy(dtype=float)
                off = ~np.eye(len(columns), dtype=bool)
                mean = float(np.nanmean(array[off])) if np.isfinite(array[off]).any() else 0.0
                array = np.where(np.isfinite(array), array, mean)
                target = np.full_like(array, mean)
                np.fill_diagonal(target, 1.0)
                array = (1 - config.correlation_shrinkage) * array + config.correlation_shrinkage * target
                array = 0.5 * (array + array.T)
                eigenvalue, eigenvector = np.linalg.eigh(array)
                eigenvalue = np.maximum(eigenvalue, 1e-8)
                array = (eigenvector * eigenvalue) @ eigenvector.T
                scale = np.sqrt(np.maximum(np.diag(array), 1e-12))
                cached_correlation = array / np.outer(scale, scale)
                cached_columns = columns
                cached_labels = (
                    average_linkage_labels(cached_correlation, config.n_clusters)
                    if config.use_cluster_weights
                    else None
                )
                last_rebuild = i
        if cached_correlation is None or len(cached_columns) == 0:
            continue
        usable = np.intersect1d(np.flatnonzero(active), cached_columns, assume_unique=True)
        if len(usable) == 0:
            continue
        in_cache = np.searchsorted(cached_columns, usable)
        annual_vol = vol.iloc[i].to_numpy(dtype=float)[usable]
        correlation = cached_correlation[np.ix_(in_cache, in_cache)]
        if config.use_cluster_weights and cached_labels is not None:
            labels = cached_labels[in_cache]
            vector[usable] *= equal_cluster_risk_multipliers(
                correlation,
                annual_vol,
                labels,
                np.ones(len(usable), dtype=bool),
            )
        cov = correlation * np.outer(annual_vol, annual_vol)
        selected = vector[usable]
        risk = float(np.sqrt(max(selected @ cov @ selected, 0.0)))
        if not np.isfinite(risk) or risk <= 0:
            continue
        vector[~np.isin(np.arange(len(vector)), usable)] = 0.0
        vector *= config.target_vol_annual / risk
        gross = float(np.abs(vector).sum())
        if gross > config.max_gross_leverage:
            vector *= config.max_gross_leverage / gross
        targets.iloc[i] = vector
    return targets, signal


def run_backtest(
    opens: pd.DataFrame,
    closes: pd.DataFrame,
    config: TrendConfig,
    funding: pd.DataFrame | None = None,
    tradeable: pd.DataFrame | None = None,
) -> BacktestResult:
    """Causal open-to-open portfolio simulation with continuous positions."""
    config.validate()
    opens, closes = opens.align(closes, join="inner", axis=0)
    opens, closes = opens.align(closes, join="inner", axis=1)
    tradeable = (
        tradeable.reindex(index=opens.index, columns=opens.columns).fillna(False)
        if tradeable is not None
        else (opens.notna() & closes.notna())
    )
    targets, _ = _target_weights(closes, config, tradeable)
    funding = (
        funding.reindex(index=opens.index, columns=opens.columns).fillna(0.0)
        if funding is not None
        else pd.DataFrame(0.0, index=opens.index, columns=opens.columns)
    )

    positions = pd.DataFrame(0.0, index=opens.index, columns=opens.columns)
    forward_frame, terminal_frame = forward_mark_returns(opens, closes)
    equity = config.initial_equity
    current = np.zeros(len(opens.columns), dtype=float)
    records: list[dict[str, float]] = []
    for i in range(len(opens) - 1):
        target = targets.iloc[i].to_numpy(dtype=float, copy=True)
        eligible = tradeable.iloc[i].to_numpy(dtype=bool)
        can_execute = np.isfinite(opens.iloc[i].to_numpy(dtype=float))
        target = np.where(eligible, target, 0.0)
        gap = target - current
        # Buffer is expressed as a fraction of each desired weight. A target
        # of zero always closes an existing position.
        tolerance = config.rebalance_buffer * np.abs(target)
        trade = np.where(np.abs(gap) > tolerance, gap - np.sign(gap) * tolerance, 0.0)
        trade = np.where((target == 0) & (current != 0), -current, trade)
        new_position = current + trade
        # Buffering may retain pieces of yesterday's book while targets move.
        # Hard portfolio constraints must bind the held book, not only the
        # pre-buffer target.
        held_gross = float(np.abs(new_position).sum())
        if held_gross > config.max_gross_leverage:
            new_position *= config.max_gross_leverage / held_gross

        # A missing open cannot execute an otherwise desired rebalance.
        new_position = np.where(can_execute, new_position, current)

        turnover = float(np.abs(new_position - current).sum())
        cost_return = turnover * config.cost_bps / 10_000.0
        terminal = terminal_frame.iloc[i].to_numpy(dtype=bool)
        next_return = forward_frame.iloc[i].to_numpy(dtype=float)
        # A disappearing contract is marked to its final observable close and
        # charged an explicit closing trade. It is not flattened for free on a
        # later row with no executable price.
        terminal_turnover = float(
            np.nansum(np.where(terminal, np.abs(new_position * (1.0 + next_return)), 0.0))
        )
        turnover += terminal_turnover
        cost_return = turnover * config.cost_bps / 10_000.0
        market_gross = new_position * next_return
        market_funding = new_position * funding.iloc[i].to_numpy(dtype=float)
        gross_return = float(np.nansum(market_gross))
        funding_return = float(np.nansum(market_funding))
        net_return = gross_return - cost_return - funding_return
        equity *= 1.0 + net_return
        positions.iloc[i] = new_position
        records.append(
            {
                "equity": equity,
                "gross_return": gross_return,
                "cost_return": cost_return,
                "funding_return": funding_return,
                "net_return": net_return,
                "turnover": turnover,
                "gross_exposure": float(np.abs(new_position).sum()),
                "net_exposure": float(new_position.sum()),
            }
        )
        # Holdings, unlike target weights, drift with their individual market
        # returns. Express the resulting notionals as weights of next equity.
        equity_factor = 1.0 + net_return
        drifted = new_position * (1.0 + np.nan_to_num(next_return))
        current = (
            drifted / equity_factor
            if np.isfinite(equity_factor) and equity_factor > 0
            else np.zeros_like(drifted)
        )
        current = np.where(terminal, 0.0, current)

    daily = pd.DataFrame(records, index=opens.index[:-1])
    metrics = performance_metrics(daily, config)
    held = positions.iloc[:-1].to_numpy(dtype=float)
    forward = forward_frame.iloc[:-1].to_numpy(dtype=float)
    gross_by_market = np.nan_to_num(held * forward)
    funding_by_market = np.nan_to_num(
        held * funding.iloc[:-1].to_numpy(dtype=float)
    )
    attribution = pd.DataFrame(
        {
            "gross_return_contribution": gross_by_market.sum(axis=0),
            "funding_return_contribution": funding_by_market.sum(axis=0),
            "long_gross_contribution": np.where(held > 0, gross_by_market, 0).sum(axis=0),
            "short_gross_contribution": np.where(held < 0, gross_by_market, 0).sum(axis=0),
            "average_absolute_weight": np.abs(held).mean(axis=0),
        },
        index=opens.columns,
    )
    return BacktestResult(
        daily=daily,
        positions=positions.iloc[:-1],
        metrics=metrics,
        attribution=attribution,
    )


def performance_metrics(daily: pd.DataFrame, config: TrendConfig) -> dict[str, float]:
    if daily.empty:
        return {}
    returns = daily["net_return"]
    years = max(len(returns) / config.annualization_days, 1 / config.annualization_days)
    total = float(daily["equity"].iloc[-1] / config.initial_equity - 1.0)
    cagr = float((1.0 + total) ** (1.0 / years) - 1.0) if total > -1 else -1.0
    std = float(returns.std(ddof=1))
    sharpe = float(returns.mean() / std * np.sqrt(config.annualization_days)) if std > 0 else 0.0
    curve = pd.concat([pd.Series([config.initial_equity]), daily["equity"].reset_index(drop=True)])
    drawdown = curve / curve.cummax() - 1.0
    return {
        "total_return": total,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
        "annual_turnover": float(daily["turnover"].sum() / years),
        "cost_drag": float(daily["cost_return"].sum()),
        "funding_drag": float(daily["funding_return"].sum()),
        "average_gross_exposure": float(daily["gross_exposure"].mean()),
    }
