# TrendBot

TrendBot is a separate, paper-only research project for testing whether a
slow, multi-horizon trend-following architecture has durable crypto expectancy.
It is not BreakerBot v4 and does not modify or share state with BreakerBot.

The initial candidate intentionally starts with the smallest useful version of
the strongest fully exposed design found during strategy archaeology:

- daily bars and next-bar execution;
- 16/48, 32/96, and 64/192-day EWMA trend components;
- trailing-only signal normalization;
- continuous long/short positions using `tanh`;
- inverse-volatility sizing;
- portfolio-level volatility targeting and a gross-exposure cap;
- buffered rebalancing;
- explicit turnover costs and optional observed funding;
- chronological design, validation, and untouched test reporting.

There are no exchange credentials, live orders, or order-submission modules.

## Quick start

Input is one CSV per market. Required columns are `timestamp`, `open`, and
`close`; optional `funding` is the signed funding rate charged to a long during
that bar.

```powershell
python scripts/fetch_archive.py --symbols BTCUSDT ETHUSDT SOLUSDT --start 2020-01 --end 2026-09
python -m trendbot.cli backtest --data data/csv --output outputs/baseline.json
python scripts/run_ablations.py --data data/csv --design-end 2023-12-31 --validation-end 2024-12-31 --output outputs/ablations.json
python -m unittest discover -s tests -v
```

The baseline is a research hypothesis, not an approved trading system. See
`docs/RESEARCH_PROTOCOL.md` before interpreting results.
