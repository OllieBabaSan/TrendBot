# TrendBot handoff

Updated: 2026-10-10

## Identity

- Standalone project: `C:\Users\user\Desktop\TrendBot`
- Purpose: validate a profitable and transferable crypto trend-following
  strategy before selecting favored tokens.
- Relationship: separate from BreakerBot, MockingBot, PressureBot, and StonkBot.
- Mode: research/backtest only.
- Live execution: unavailable by design.

## Initial candidate

- Daily bars with signals lagged before next-open execution.
- Three EWMA trend speeds: 16/48, 32/96, and 64/192 days.
- Continuous long/short response using `tanh`.
- Inverse-volatility sizing and portfolio volatility targeting.
- 20% annual target volatility, 1.5x gross cap, and 10% rebalance buffer.
- Default trading cost: 10 basis points per unit of turnover.
- Observed funding may be supplied in input data and is charged by position sign.

These values are a frozen starting hypothesis, not optimized TrendBot settings.

## Current state

- Core research engine, Binance monthly archive fetcher/parser, CSV loader,
  chronological evaluator, market attribution, and ablation runner implemented.
- Eleven tests pass, covering causal timing, position modes, positive trend
  response, deterministic accounting, cost drag, gross-cap enforcement,
  archive parsing, prior-day eligibility, disjoint chronological splits,
  fast-horizon availability for young markets, and delisting marks/exits.
- An initial BTC/ETH/SOL 2023-2025 engineering smoke test is documented in
  `docs\INITIAL_SMOKE_TEST.md`. Its original figures were superseded after a
  fast-horizon availability mismatch was corrected; the corrected 2025 test
  was still negative (-3.73%). It is not a validated candidate.
- A 638-market point-in-time 2020-2025 baseline and structural ablations are
  documented in `docs\FULL_UNIVERSE_BASELINE.md`. The aggregate result is
  promising (+194.02%, Sharpe 0.92), but 2023 lost 19.26%, so it fails the
  positive-validation gate and is not approved for paper trading.
- No scheduled task or resident process exists.

## Next work

1. Add portfolio correlation clustering/equal cluster-risk allocation and
   compare it with the current shrunk-correlation risk target.
2. Complete funding-coverage, monthly/regime, liquidity-threshold, and
   leverage-cap diagnostics.
3. Compare the fully reproduced reference construction with the simplified
   TrendBot baseline using identical dates and eligibility.
4. Add attribution by regime, month, and best contributors plus explicit
   concentration gates.
5. Add missing-data, funding-sign, delayed-fill, correlation-spike, and
   accounting invariance tests.
6. Start a forward paper lane only if the final candidate passes the declared
   historical and robustness gates.
