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
- Nine tests pass, covering causal timing, position modes, positive trend
  response, deterministic accounting, cost drag, gross-cap enforcement,
  archive parsing, prior-day eligibility, and disjoint chronological splits.
- An initial BTC/ETH/SOL 2023-2025 engineering smoke test is documented in
  `docs\INITIAL_SMOKE_TEST.md`. The baseline failed its 2025 untouched-test
  gate (-6.07%) and is not a validated candidate.
- No scheduled task or resident process exists.

## Next work

1. Extend collection from the three-market smoke cohort to a point-in-time
   liquid perpetual universe, including delisted contracts.
2. Add portfolio correlation shrinkage/clustering and compare it with the
   current rolling sample-covariance risk target.
3. Add attribution by regime, month, and best contributors plus explicit
   concentration gates.
4. Add missing-data, funding-sign, delayed-fill, correlation-spike, and
   accounting invariance tests.
5. Reproduce the remaining exposed reference architecture before introducing
   strategy changes.
6. Repeat predeclared ablations on the full point-in-time universe.
7. Start a forward paper lane only if untouched historical gates pass.
