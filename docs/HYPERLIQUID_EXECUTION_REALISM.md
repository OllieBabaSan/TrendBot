# Hyperliquid execution-realism gate

Date: 2026-10-13

## Scope

This gate applies venue mechanics to the reduced, decision-relevant research
set. It does not place orders or enable paper/live execution.

Active comparisons:

- T1 architectural control, base scenario only.
- Frozen 50% transition-valve control.
- Long-only 10-bps-equivalent diagnostic boundary, base scenario only.
- Frozen exploratory all-long/top-liquidity-third-short hybrid.

Archived 75%, short-only, and redundant long-only cost runs are not recomputed.

## Venue and model assumptions

- Primary account: $5,000; $2,500 sensitivity and archived $10,000 reference.
- Hyperliquid base-tier taker fee: 4.5 bps per traded notional.
- Minimum order notional: $10.
- Market-specific lot increments from the captured `szDecimals` metadata.
- Slippage floor: 1 bp.
- Causal square-root impact estimate using prior 30-day median absolute return
  and prior 30-day median quote volume.
- Baseline impact coefficient 0.5; adverse-impact coefficient 1.0.
- A separate one-day target-delay stress.

Historical L2 order books are unavailable. The impact model is a disclosed
estimate, not reconstructed fills. Current size precision is applied
historically.

## Results

| Variant/scenario | Return | Sharpe | Drawdown | 2023 | 2024-25 |
|---|---:|---:|---:|---:|---:|
| T1 / $5k venue base | +14.48% | 0.217 | -36.53% | +34.60% | -20.83% |
| 50% control / $5k venue base | +27.63% | 0.331 | -30.05% | +33.86% | -12.59% |
| Long-only boundary / $5k venue base | +37.14% | 0.434 | -20.18% | +8.41% | +5.07% |
| Hybrid / $5k venue base | **+41.58%** | **0.486** | **-25.46%** | **+20.22%** | **+1.78%** |
| 50% control / $5k impact stress | +27.23% | 0.328 | -30.17% | +33.78% | -12.77% |
| Hybrid / $5k impact stress | +41.67% | 0.487 | -25.42% | +20.09% | +1.95% |
| 50% control / $5k one-day delay | +29.27% | 0.343 | -31.45% | +43.45% | -13.63% |
| Hybrid / $5k one-day delay | +46.82% | 0.533 | -25.20% | +22.87% | +3.69% |
| Hybrid / $2,500 account | +39.90% | 0.466 | -26.05% | +20.14% | +0.52% |
| Hybrid / archived $10k reference | +43.67% | 0.507 | -25.25% | +20.07% | +3.48% |

The one-day delay result is robustness evidence only. It must not be promoted
as an optimized timing rule.

## Execution diagnostics

At $5,000, the hybrid's modeled all-in execution cost is 5.91 bps per unit of
turnover (4.5-bps fee plus modeled slippage). The adverse-impact case raises it
to 6.32 bps with little change in ordering.

The $5,000 venue-base hybrid has:

- 57,542 rebalance requests over all market-days.
- 20,582 repeated requests below the $10 minimum (35.8%).
- Average absolute portfolio target-tracking error of 1.90 percentage points.
- Maximum target-tracking error of 11.22 percentage points.

These are predominantly repeated tiny buffer/dust adjustments, not 20,582
independent missed entries. At $2,500, the rejection fraction rises to 42.3%,
average tracking error to 2.72 points, and 2024-2025 return falls near zero.
That account size is operationally marginal for this broad portfolio.

## Decision

The liquidity-restricted hybrid passes this execution-mechanics gate at a
$5,000 research account and remains superior to the 50% control under the
adverse-impact and delay stresses. Lot sizes and the $10 minimum do not explain
away the result.

This does not validate profitability. Hyperliquid Sharpe remains modest, the
2024-2025 margin is thin, historical order-book fills are modeled, and the
candidate was discovered post-hoc. Freeze the implementation and begin a
strictly paper-only $5,000 forward comparison against T1 and the 50% control. Do not
change the liquidity percentile or promote delayed execution.
