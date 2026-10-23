# T1 disagreement safety-valve study

Date: 2026-10-10

## Purpose

Test whether the 16/48-day sleeve can act as a causal warning that reduces the
cost of T1's slower adaptation without destroying the multi-horizon trend
payoff. The frozen T1 remains the incumbent; no live or paper strategy changed.

## Predeclared constructions

All valves are applied per market after normal T1 risk sizing and before the
existing rebalance buffer. They use only lagged component signals.

- **Consensus:** exposure varies with signed agreement among all available
  speed sleeves.
- **Fast transition:** exposure is reduced whenever 16/48 opposes the average
  sign of 32/96 and 64/192.
- **Slow inertia:** exposure is reduced only when that disagreement exists and
  the combined T1 target still follows the slower sign. This target-aware
  construction tests whether the broad brake accidentally suppresses positions
  that have already adapted.

Each construction was tested with residual-exposure floors of 0%, 25%, 50%,
and 75%, at 10 and 20 basis points. The grid was fixed before reviewing the
target-aware results. No price-return, drawdown, or calendar filter was used.

## Main results at 10 bps

| Variant | Total return | Sharpe | Max drawdown | 2023 | 2024-2025 |
|---|---:|---:|---:|---:|---:|
| Frozen T1 | +194.45% | 0.931 | -29.26% | -19.49% | +50.29% |
| Consensus, 50% floor | +180.91% | 0.931 | -25.55% | -15.71% | +42.59% |
| Fast transition, 50% floor | +182.39% | 0.926 | -25.68% | -12.62% | +42.47% |
| Fast transition, 75% floor | +188.50% | 0.932 | -26.76% | -16.24% | +47.01% |
| Slow inertia, 50% floor | +182.13% | 0.925 | -25.69% | -12.30% | +42.14% |
| Slow inertia, 75% floor | +188.37% | 0.932 | -26.77% | -16.09% | +46.85% |

At 20 bps the ordering remains coherent. Frozen T1 returns +174.45% with
0.878 Sharpe and a -30.42% drawdown. The 50% fast-transition brake returns
+163.33% with 0.871 Sharpe, a -26.39% drawdown, and a -14.05% 2023 result.
The 75% version returns +169.33% with 0.879 Sharpe, a -27.54% drawdown, and a
-17.61% 2023 result.

## Interpretation

The result is a smooth protection-versus-power curve rather than an isolated
winning parameter. Stronger braking consistently reduces the transition loss
and drawdown while surrendering return in ordinary trend periods. Neighboring
floors and the 20-bps stress preserve the direction of the result, which is
evidence for a real mechanism.

The target-aware slow-inertia rule is almost indistinguishable from the broad
fast-transition rule and does not improve its tradeoff. The protection is
therefore associated with disagreement itself, not with a special ability to
identify only stale slow-side positions.

The 50% fast-transition floor is the strongest protection/power research
candidate: it removes about 6.9 percentage points of the 2023 loss and 3.6
points of maximum drawdown while giving up about 12.1 points of cumulative
return. The 75% floor is the conservative neighbor: it preserves nearly all
Sharpe and more upside, but removes only about 3.3 points of the 2023 loss.

Neither makes 2023 profitable. The safety valve improves T1 but does not yet
establish regime transferability or justify paper promotion. Selecting 50%
versus 75% from these already inspected years would be optimization. Retain
both as frozen finalists for attribution, stress testing, and genuinely new
forward evidence.

## Next checks

1. Attribute the 50% and 75% candidates by market, month, long/short side, and
   disagreement episode to verify that protection is not concentrated in a
   few names or one short interval.
2. Stress delayed execution, funding sign, higher transaction costs, and
   correlation spikes using the same frozen floors.
3. Compare the valves on an accessible intended execution venue before any
   paper promotion.
4. Do not add more floor values unless new data falsifies both frozen
   finalists; the existing curve already describes that parameter dimension.

