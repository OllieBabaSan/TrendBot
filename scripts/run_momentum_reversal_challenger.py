from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from trendbot.backtest import forward_mark_returns
from trendbot.binance_archive import point_in_time_eligibility
from trendbot.data import load_csv_panels


YEARS = range(2020, 2026)


def challenger_signal(close: pd.DataFrame, returns: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    output = pd.DataFrame(index=close.index, columns=close.columns, dtype=float)
    for symbol in close.columns:
        price, ret, vol = close[symbol], returns[symbol], volume[symbol]
        vol_z = (vol - vol.rolling(21).mean()) / (vol.rolling(21).std() + 1e-9)
        vol_multiplier = 1.0 + np.tanh(vol_z)
        reversal = 0.6 * -(price / price.shift(3) - 1) + 0.4 * -(price / price.shift(5) - 1)
        momentum = (
            0.3 * (price / price.shift(7) - 1)
            + 0.4 * (price / price.shift(14) - 1)
            + 0.3 * (price / price.shift(21) - 1)
        ) * vol_multiplier
        trend_strength = (
            price.ewm(span=12).mean() - price.ewm(span=26).mean()
        ) / price
        vol_21 = ret.rolling(21).std() * np.sqrt(365)
        vol_zscore = (vol_21 - vol_21.rolling(60).mean()) / (vol_21.rolling(60).std() + 1e-9)
        consistency = ret.rolling(21).apply(lambda values: (values > 0).sum() / len(values))
        trend = (consistency - 0.5) * 2
        regime = (-0.5 * vol_zscore.clip(-1, 1) + 0.5 * trend.clip(-1, 1)).clip(-1, 1)
        raw = (
            (0.55 - 0.15 * regime) * reversal
            + (0.35 + 0.15 * regime) * momentum
            + 0.10 * trend_strength * 100
        )
        output[symbol] = ((raw - raw.rolling(60).mean()) / (raw.rolling(60).std() + 1e-9)).shift(1)
    return output


def ranked_targets(signal: pd.DataFrame, eligible: pd.DataFrame, exclude_btc: bool) -> pd.DataFrame:
    targets = pd.DataFrame(0.0, index=signal.index, columns=signal.columns)
    for date in signal.index:
        active = eligible.loc[date] & signal.loc[date].notna()
        if exclude_btc and "BTCUSDT" in active:
            active.loc["BTCUSDT"] = False
        row = signal.loc[date, active]
        if len(row) < 10:
            continue
        ranked = row.rank(method="average")
        demeaned = ranked - ranked.mean()
        gross = float(demeaned.abs().sum())
        if gross > 0:
            targets.loc[date, row.index] = demeaned / gross
    return targets


def beta_project(weights: np.ndarray, beta: np.ndarray, active: np.ndarray) -> np.ndarray:
    indexes = np.flatnonzero(active & np.isfinite(beta))
    if len(indexes) < 3:
        return weights
    matrix = np.vstack([np.ones(len(indexes)), beta[indexes]])
    gram = matrix @ matrix.T
    correction = matrix.T @ np.linalg.pinv(gram) @ (matrix @ weights[indexes])
    answer = weights.copy()
    answer[indexes] -= correction
    return answer


def simulate(targets, opens, closes, funding, betas, caps, cost_bps, constrained):
    forward, terminal = forward_mark_returns(opens, closes)
    dates, columns = opens.index[:-1], opens.columns
    current = np.zeros(len(columns))
    equity = 10_000.0
    return_history: list[float] = []
    rows = []
    for date in dates:
        desired = targets.loc[date].to_numpy(dtype=float).copy()
        active = desired != 0
        if constrained:
            desired = beta_project(desired, betas.loc[date].to_numpy(dtype=float), active)
            limit = caps.loc[date].to_numpy(dtype=float)
            desired = np.clip(desired, -limit, limit)
        if len(return_history) >= 21:
            realized = float(np.std(return_history[-21:], ddof=1) * np.sqrt(365))
            scalar = float(np.clip(0.14 / realized, 0.6, 1.4)) if realized > 1e-9 else 1.0
        else:
            scalar = 1.0
        desired *= scalar
        can_execute = opens.loc[date].notna().to_numpy(dtype=bool)
        held = np.where(can_execute, desired, current)
        turnover = float(np.abs(held - current).sum())
        period_return = forward.loc[date].to_numpy(dtype=float)
        is_terminal = terminal.loc[date].to_numpy(dtype=bool)
        turnover += float(np.nansum(np.where(is_terminal, np.abs(held * (1 + period_return)), 0.0)))
        gross = float(np.nansum(held * period_return))
        funding_cost = float(np.nansum(held * funding.loc[date].to_numpy(dtype=float)))
        cost = turnover * cost_bps / 10_000
        net = gross - funding_cost - cost
        equity *= 1 + net
        return_history.append(net)
        drifted = held * (1 + np.nan_to_num(period_return))
        current = drifted / (1 + net) if 1 + net > 0 else np.zeros_like(drifted)
        current = np.where(is_terminal, 0.0, current)
        rows.append({"equity": equity, "net_return": net, "gross_return": gross, "funding_return": funding_cost, "cost_return": cost, "turnover": turnover, "gross_exposure": float(np.abs(held).sum()), "net_exposure": float(held.sum())})
    return pd.DataFrame(rows, index=dates)


def stats(daily: pd.DataFrame) -> dict:
    returns = daily["net_return"]
    curve = (1 + returns).cumprod()
    drawdown = curve / curve.cummax() - 1
    std = float(returns.std(ddof=1))
    return {
        "return": float(curve.iloc[-1] - 1),
        "sharpe": float(returns.mean() / std * np.sqrt(365)) if std > 0 else 0.0,
        "max_drawdown": float(drawdown.min()),
        "average_gross_exposure": float(daily["gross_exposure"].mean()),
        "annual_turnover": float(daily["turnover"].sum() / (len(daily) / 365)),
        "funding_drag": float(daily["funding_return"].sum()),
        "cost_drag": float(daily["cost_return"].sum()),
    }


def summarize(daily: pd.DataFrame) -> dict:
    return {
        "full": stats(daily),
        "yearly": {str(year): stats(daily.loc[f"{year}-01-01":f"{year}-12-31"]) for year in YEARS},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    panels = load_csv_panels(args.data)
    opens, closes = panels["open"], panels["close"]
    funding, volume = panels["funding"], panels["quote_volume"]
    returns = closes.pct_change(fill_method=None)
    eligible = point_in_time_eligibility(volume, closes)
    signal = challenger_signal(closes, returns, volume)
    source_signal = signal.copy()
    if "BTCUSDT" in source_signal.columns:
        # Match the notebook's implementation before cross-sectional ranking.
        # Ranking this zero later gives BTC a nonzero target; the intended
        # variant also removes BTC from the eligible set.
        source_signal["BTCUSDT"] = 0.0
    btc = returns["BTCUSDT"]
    betas = returns.rolling(60).cov(btc).div(btc.rolling(60).var(), axis=0).shift(1)
    caps = ((volume.shift(1).rolling(30, min_periods=15).mean() * 0.05) / 10_000_000).clip(upper=0.18 / 1.4).fillna(0.0)

    variants = {}
    for exclude_btc in (False, True):
        targets = ranked_targets(source_signal, eligible, exclude_btc)
        for constrained in (False, True):
            for cost in (10.0, 20.0):
                name = f"{'intended_no_btc' if exclude_btc else 'published_btc_rank_bug'}_{'liquidity_beta' if constrained else 'signal_only'}_{int(cost)}bps"
                print(f"running {name}", flush=True)
                variants[name] = summarize(simulate(targets, opens, closes, funding, betas, caps, cost, constrained))
    payload = {
        "status": "independent_core_reproduction",
        "source": {"repository": "https://github.com/shantanupatil14/Crypto-Cross-Sectional-Statistical-Arbitrage", "commit": "f01f132e5417ea33b5095d4e72ed0f46eb363983"},
        "method": "Reproduces the exposed final signal on TrendBot's point-in-time universe. Signal-only isolates alpha; liquidity_beta adds the disclosed ADTV caps and a deterministic dollar/beta-neutral projection in place of unavailable CVXPY.",
        "known_source_issue": "The published notebook sets BTC raw signal to zero before ranking, which assigns BTC a nonzero ranked target. Both published and intended exclusions are tested.",
        "variants": variants,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({name: value["full"] for name, value in variants.items()}, indent=2))


if __name__ == "__main__":
    main()
