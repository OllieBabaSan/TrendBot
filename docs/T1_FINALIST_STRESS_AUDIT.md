# T1 finalist attribution and stress audit

Date: 2026-10-11

## Scope

This audit freezes three constructions: original T1, the 50% residual-exposure
fast-transition valve, and its 75% neighbor. It does not search new valve
parameters. The complete result ledger is
`outputs\t1-finalist-stress-audit.json`.

## Attribution

The 50% candidate is not dominated by a handful of markets. Its largest market
supplies 6.2% of positive gross contribution and its top five supply 22.3%.
There are 317 positive and 181 negative contributing markets. Original T1 is
similar at 6.3%, 22.8%, 311, and 187 respectively.

Across the complete sample, the 50% candidate's gross contribution is +1.31
from long positions and +0.06 from shorts. The system is therefore not secretly
dependent on a persistent short premium, even though slow short adaptation was
important during the 2023 reversal.

The 2023 improvement is distributed but not universal. Relative to T1, the 50%
valve materially improves January, February, October, and November; March is
about 1.4 percentage points worse. Six of the twelve months are positive for
the valve. This supports a genuine transition-risk effect but rejects the idea
that disagreement protects every reversal episode.

On 221 causally classified high-co-movement days, all candidates remain
profitable. Mean daily returns are 3.11 bps for T1, 3.52 bps for the 50% valve,
and 3.37 bps for the 75% valve, versus 5.86, 5.55, and 5.70 bps on ordinary
days. Correlation spikes reduce efficiency but do not invert expectancy in
this sample.

## Operational stresses

| Construction | Control return / Sharpe / DD | +2-day delay | 50-bps cost | Adverse funding |
|---|---|---|---|---|
| T1 | +194.45% / 0.931 / -29.26% | +177.02% / 0.876 / -25.72% | +122.20% / 0.717 / -33.80% | +92.04% / 0.606 / -35.72% |
| 50% valve | +182.39% / 0.926 / -25.68% | +191.07% / 0.942 / -21.44% | +113.50% / 0.705 / -28.46% | +89.57% / 0.611 / -29.58% |
| 75% valve | +188.50% / 0.932 / -26.76% | +184.40% / 0.912 / -22.45% | +119.11% / 0.718 / -30.95% | +90.80% / 0.610 / -32.82% |

Extra one- and two-day delays do not destroy any candidate. Some delayed cases
improve historically; this is evidence against timing fragility, not a reason
to optimize an intentional delay. All candidates remain profitable at 20, 30,
and 50 bps, with expected monotonic deterioration.

Observed funding is a material drag. The deliberately severe adverse case
charges the absolute observed funding rate against both long and short
notional. It roughly halves cumulative return but leaves all three candidates
positive. Venue-specific funding and contract mechanics must still replace
this generic stress before paper promotion.

## Decision

Both valves survive the falsification audit. The 50% valve is the provisional
risk-control lead because it provides more consistent drawdown and transition
protection under delay and adverse funding. The 75% valve remains the
minimal-change comparator and preserves slightly more unstressed upside.

This is not sufficient for forward paper operation. Every historical period is
already inspected, and the archive venue is not available to the user for
execution. The next phase is to reproduce both frozen finalists on one
accessible intended venue using its actual instruments, history, funding,
fees, minimum sizes, and executable universe. No further safety-valve tuning
should occur before that reproduction.

The full regression suite passes 32 tests after adding causal delay and funding
stress support.

