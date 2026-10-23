# TrendBot handoff

Updated: 2026-10-10

## Identity

- Standalone project: `C:\Users\user\Desktop\TrendBot`
- Purpose: validate a profitable and transferable crypto trend-following
  strategy before selecting favored tokens.
- Relationship: separate from BreakerBot, MockingBot, PressureBot, and StonkBot.
- Mode: research/backtest only.
- Live execution: unavailable by design.

## Venue constraint

The user does not have Binance trading access. Binance archives are a broad
historical research source only. Binance must not become TrendBot's execution
foundation, live operational dependency, or authority for the eventual
tradable universe. Any candidate that survives discovery must be reproduced on
an accessible intended execution venue using that venue's instruments,
liquidity, funding, fees, order rules, and executable fills before forward
paper promotion.

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
- Twenty-five tests pass, covering causal timing, position modes, positive trend
  response, deterministic accounting, cost drag, gross-cap enforcement,
  archive parsing, prior-day eligibility, disjoint chronological splits,
  fast-horizon availability for young markets, and delisting marks/exits.
- Average-linkage clustering and equal cluster-risk allocation are implemented
  and tested without SciPy. A held-book audit also corrected post-buffer gross
  exposure enforcement; maximum exposure now respects the 1.5x ceiling.
- An initial BTC/ETH/SOL 2023-2025 engineering smoke test is documented in
  `docs\INITIAL_SMOKE_TEST.md`. Its original figures were superseded after a
  fast-horizon availability mismatch was corrected; the corrected 2025 test
  was still negative (-3.73%). It is not a validated candidate.
- A 638-market point-in-time 2020-2025 baseline and structural ablations are
  documented in `docs\FULL_UNIVERSE_BASELINE.md`. The aggregate result is
  promising (+193.87%, Sharpe 0.92), but 2023 lost 19.26%, so it fails the
  positive-validation gate and is not approved for paper trading.
- Cluster and operational diagnostics are in
  `docs\CLUSTER_AND_DIAGNOSTICS.md`. Cluster-count sensitivity is high and no
  cluster variant repairs 2023, so cluster weighting has not replaced the
  control. Funding archive coverage is 99.777%; liquidity sensitivity is
  coherent from $1M through $25M median quote-volume thresholds.
- No scheduled task or resident process exists.

### Reference reproduction and accounting correction

- `docs\REFERENCE_REPRODUCTION.md` compares the public Trend Atlas engine at
  commit `4aaa229f5bc9f1b762ba4f6ba5d83c9f5cfef294` on the same universe.
- The exact public default was inferior: +136.19%, Sharpe 0.838, drawdown
  -32.11%. Do not copy it wholesale.
- Its no-cluster blended-volatility variant was the strongest reference
  neighbor (+167.15%, Sharpe 0.950, drawdown -21.89%, 2023 -12.66%), but still
  failed 2023 and trailed the corrected control in 2024-2025. It is not
  promoted.
- Corrected a real accounting simplification: positions now drift with market
  returns, missing opens freeze execution, temporary gaps preserve P&L, and
  terminal settlement occurs only after the final observable open.
- Corrected baseline: +194.45%, Sharpe 0.931, drawdown -29.26%, 2023 -19.49%,
  2024-2025 +50.29%. The prior economic conclusion survives.
- Full unittest suite at the reference-reproduction checkpoint: 27 tests pass.

### Volatility-blend study

- `docs\VOLATILITY_BLEND_STUDY.md` reports a predeclared 0%, 25%, 50%, 70%,
  and 100% short-volatility grid, with the balance in expanding long volatility,
  at both 10 and 20 bps.
- The result is a monotonic risk-return dial, not a fix. Long-heavy blends reduce
  2023 loss and drawdown; short-heavy blends preserve upside.
- 50/50 and 70/30 had the best 10-bps Sharpe (0.945 and 0.944), with neighboring
  agreement at 20 bps, but every point still lost money in 2023.
- No blend is promoted. Candidate T1 remains a benchmark but has not demonstrated
  the required regime transferability. Stop locally tuning its volatility mix.
- Full unittest suite after adding configurable volatility forecasts: 28 pass.

### External challenger tournament

- `docs\CHALLENGER_TOURNAMENT.md` records the bounded public-code and
  strategy-family challenge performed before concentrating on T1.
- The independently reconstructed cross-sectional momentum/reversal challenger
  was positive at 10 bps (+111.93%, Sharpe 0.922) but lost in 2022 and 2023,
  suffered -29.65% drawdown, and deteriorated to +39.67% / 0.451 Sharpe at
  20 bps. It does not displace T1.
- The source repository's advertised holdout is repeatedly inspected and its
  BTC exclusion is implemented incorrectly. Both published behavior and the
  intended exclusion are preserved in
  `outputs\momentum-reversal-challenger.json`.
- Public stat-arb candidates did not provide reproducible data/results; basis
  carry requires hedge-leg and execution data TrendBot does not possess; HFT
  repositories expose infrastructure rather than portable alpha.
- T1 remains the strongest tested incumbent, not a validated live candidate.
  Its 2023 transition failure still blocks promotion. The next focused study
  is a predeclared causal disagreement/exposure safety valve, with the external
  challenger frozen as a comparator.
- Full unittest suite at this checkpoint: 28 tests pass.

### T1 disagreement safety valve

- `docs\DISAGREEMENT_SAFETY_VALVE.md` and
  `outputs\disagreement-safety-valve.json` preserve the causal safety-valve
  study. No production or paper configuration changed.
- Consensus, broad fast-versus-slow disagreement, and target-aware slow-inertia
  brakes were tested at frozen 0%, 25%, 50%, and 75% residual-exposure floors
  under both 10 and 20 bps costs.
- Results form a coherent protection/power curve. At 10 bps the 50% broad
  fast-transition brake returned +182.39%, Sharpe 0.926, drawdown -25.68%, and
  2023 -12.62%, versus frozen T1 at +194.45%, 0.931, -29.26%, and -19.49%.
- The 75% neighbor returned +188.50%, Sharpe 0.932, drawdown -26.76%, and 2023
  -16.24%. The ordering remained coherent at 20 bps.
- The target-aware correction did not improve the tradeoff. Disagreement itself
  supplies the protection; the evidence does not isolate only stale slow-side
  positions.
- Retain the 50% and 75% fast-transition floors as frozen research finalists.
  Neither makes 2023 profitable, and selecting between them on inspected years
  would be optimization. Run attribution and operational stresses before any
  paper consideration.
- Full unittest suite at this checkpoint: 31 tests pass.

### T1 finalist attribution and stress audit

- `docs\T1_FINALIST_STRESS_AUDIT.md` and
  `outputs\t1-finalist-stress-audit.json` preserve the frozen-finalist audit.
- The 50% valve is broadly distributed: top market 6.2% and top five 22.3% of
  positive gross contribution; 317 markets positive and 181 negative.
- Its 2023 protection spans multiple months but is not universal. January,
  February, October, and November improve materially, while March worsens.
- T1 and both valves remain profitable under one- and two-day extra delays,
  20/30/50-bps costs, and a severe adverse-funding construction. Historical
  improvement under delay is robustness evidence, not a parameter proposal.
- A causal high-co-movement regime has lower mean daily returns but positive
  expectancy for all candidates. The 50% valve has the strongest high-regime
  mean of the three.
- The 50% valve is the provisional risk-control lead; the 75% valve remains the
  minimal-change comparator. Both now require reproduction on an accessible
  intended execution venue. Do not tune the valve further on inspected data.
- Full unittest suite at this checkpoint: 32 tests pass.

### Hyperliquid venue transfer

- Hyperliquid is the intended primary venue; GMX remains a future secondary
  venue if its market coverage expands.
- `src\trendbot\hyperliquid_archive.py` and
  `scripts\fetch_hyperliquid_archive.py` implement a public, read-only,
  resumable metadata/candle/funding collector. No wallet or trading endpoint is
  used.
- The 2026-10-11 snapshot contains 234 main-perpetual markets, including 56
  delisted, with all 234 candle fetches successful. Ninety-nine markets ever
  pass the unchanged causal history/liquidity gate; median simultaneous breadth
  is 21, maximum 45, and latest breadth 33.
- `docs\HYPERLIQUID_TRANSFER_SCREEN.md` and
  `outputs\hyperliquid-transfer-screen-no-funding.json` record the preliminary
  zero-funding transfer gate.
- On Hyperliquid at 10 bps: T1 +34.64% / Sharpe 0.378 / drawdown -31.74%; frozen
  50% valve +50.02% / 0.497 / -24.71%; frozen 75% valve +41.24% / 0.430 /
  -28.50%. Both valves transfer directionally, but both lose in 2024-2025.
- Do not promote the historically tested zero-floor variant merely because it
  scores best on this newly inspected venue sample. Keep 50% and 75% frozen.
- Exact hourly funding, venue fees/order constraints, and executable slippage
  remain required. Current transfer figures are explicitly no-funding and do
  not authorize paper or live execution.
- Full unittest suite at this checkpoint: 35 tests pass.

### Hyperliquid funded transfer

- `scripts\fetch_hyperliquid_candidate_funding.py` collected funding only for
  97 markets and 23,344 market-days on which frozen T1 could hold exposure.
- Coverage is approximately 99.996% of expected funding intervals. The audit
  found 17 hourly days missing one record and two early three-observation days
  missing entirely. These gaps are disclosed in the manifest and are far too
  small to explain the result.
- Collector reliability fixes are committed: transient 5xx responses retry and
  original case-sensitive API names such as `kBONK` are preserved.
- `docs\HYPERLIQUID_FUNDED_TRANSFER.md` and
  `outputs\hyperliquid-transfer-funded.json` preserve the funded comparison.
- At 10 bps: T1 +13.03% / Sharpe 0.204 / drawdown -37.08%; frozen 50% valve
  +26.10% / 0.318 / -30.43%; frozen 75% valve +18.65% / 0.254 / -34.01%.
- The 50% valve remains best at 20 bps (+20.40%, Sharpe 0.270), but loses
  14.94% in 2024-2025. Observed funding materially reduces all candidates.
- The safety mechanism transfers, but the funded strategy fails the paper
  promotion gate. Do not enable forward paper or retune on this inspected
  venue period.
- Full unittest suite at this checkpoint: 36 tests pass.

### Hyperliquid funded attribution

- `scripts\run_hyperliquid_funded_attribution.py`,
  `outputs\hyperliquid-funded-attribution.json`, and
  `docs\HYPERLIQUID_FUNDED_ATTRIBUTION.md` preserve an exact additive audit of
  the unchanged 10-bps funded finalists. Daily reconstruction error is below
  1.4e-17.
- For the 50% valve, longs contributed +39.91 arithmetic net points and shorts
  -8.48. In 2024-2025, longs remained +11.58 while shorts lost 20.61; short
  timing, not funding alone, was the dominant failure.
- Funding still matters: it consumed 17.44 points overall and 11.91 of 24.89
  long gross points in 2024-2025. However, funding-paying observations were
  profitable while funding-receiving observations lost, so a naive funding-sign
  filter would be adverse.
- The 50% valve correctly reduces a losing disagreement state (-12.75 net), but
  the edge is concentrated: 38 of 97 markets were positive and removing the top
  five winners changes +30.81 arithmetic net points to -3.44.
- Do not promote or tune. Next diagnose short-sleeve stability under causal
  partitions and realistic execution; use only an economically defined funding
  burden if testing a new funding control.
- Full unittest suite at this checkpoint: 37 tests pass.

### Side and liquidity diagnostic

- `scripts\run_hyperliquid_side_diagnostics.py`,
  `outputs\hyperliquid-side-diagnostics.json`,
  `outputs\binance-side-diagnostics.json`, and
  `docs\SIDE_AND_LIQUIDITY_DIAGNOSTIC.md` preserve the cross-venue audit.
- Long-only is not a general fix. It improves funded Hyperliquid to +38.84% /
  0.455 Sharpe / -19.95% drawdown, but on the broad archive it underperforms
  long/short, suffers -36.36% drawdown, and loses heavily in 2022.
- Short-only is rejected: approximately flat on Hyperliquid and -26.17% on the
  broad archive.
- BTC regime, age, and prior funding burden do not identify a stable short-side
  gate. The top prior-liquidity third is the only economically plausible bucket
  with positive short contribution on both venues.
- A deliberately post-hoc exploratory hybrid retains all 50%-valve longs and
  allows shorts only in the causal top third of prior 30-day median liquidity.
  At 10 bps it returns +42.57% / 0.499 / -25.31% on funded Hyperliquid and
  +185.81% / 1.092 / -20.08% on the 638-market archive. It remains ordered at
  20/30 bps and positive after removing its top five markets.
- This is the strongest new research hypothesis, not a validated model. The
  liquidity boundary was selected after attribution, Hyperliquid evidence is
  still weak, and 2025 remains negative on the broad archive. Freeze the rule;
  do not optimize its percentile on these samples.
- Full unittest suite at this checkpoint: 38 tests pass.

### Hyperliquid execution-realism gate

- `scripts\run_hyperliquid_execution_realism.py`,
  `outputs\hyperliquid-execution-realism.json`, and
  `docs\HYPERLIQUID_EXECUTION_REALISM.md` preserve the reduced active-set gate.
- The simulator applies current Hyperliquid `szDecimals` lot sizes, the $10
  minimum notional, 4.5-bps base-tier taker fees, a 1-bp slippage floor, and a
  causal square-root impact estimate from prior volatility and quote volume.
- The primary approachable account is now $5,000. The hybrid returns +41.58% /
  0.486 Sharpe / -25.46% drawdown versus +27.63% / 0.331 / -30.05% for the 50%
  control. It remains +41.67% under doubled modeled impact and +46.82% with a
  one-day delay.
  The delay result is robustness evidence, not a parameter proposal.
- At $5,000, hybrid effective modeled execution cost is 5.91 bps per turnover
  unit, rising to 6.32 bps under impact stress. Average target-tracking error is
  1.90 percentage points and 35.8% of repeated rebalance requests fall below
  $10. The archived $10,000 reference remains +43.67% / 0.507 / -25.25%.
- A $2,500 account is marginal: 42.3% subminimum attempts, 2.72-point average
  tracking error, and only +0.52% in 2024-2025.
- The hybrid passes the venue-mechanics gate at $5,000 but remains post-hoc and
  historically modeled. Freeze it for a paper-only forward comparison; do not
  optimize liquidity percentile or delay.
- Full unittest suite at this checkpoint: 40 tests pass.

### 2023 transition-loss attribution

- `docs\TRANSITION_LOSS_AUDIT_2023.md` and
  `outputs\transition-loss-attribution-2023.json` contain the audit.
- 2023 baseline: -19.26% net. Long gross contribution +23.91%; short gross
  contribution -41.34%.
- January's loss was dominated by positions aged 91+ days (-13.79% gross);
  March losses concentrated in 4-30-day positions.
- Single-speed 2023 results: 16/48 +1.90%, 32/96 -6.48%, 64/192 -17.79%.
  Fast-only is not a complete fix because it lost 13.27% in March and was weak
  in the chronological holdout.
- The strongest next experiment is a predeclared equal-risk ensemble of
  independently constructed speed sleeves, assessed with anchored walk-forward
  folds. It was run and is not promoted: 2023 improved to -6.78% and maximum
  drawdown to -22.91%, but full Sharpe fell to 0.82 and 2024-2025 return fell
  to +14.80%. Do not optimize sleeve weights on the inspected years.

## Next work

1. Implement a strictly paper-only daily forward comparison of frozen T1,
   frozen 50%, and the frozen liquidity-restricted hybrid at a $5,000 ledger.
2. Preserve identical market data, timestamps, venue rules, funding, and fill
   assumptions across all three lanes; report tracking errors and missed orders.
3. Do not optimize the liquidity percentile, delay, or impact assumptions on
   forward observations.
4. Keep wallet credentials and live execution unavailable by design.
