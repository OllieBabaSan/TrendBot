# Binance perpetual archive universe catalog

Generated: 2026-10-10

## Scope

TrendBot enumerated the public Binance USD-margined monthly archive by
historical contract directory and daily timeframe. It did not use the current
exchange listing as its universe, so contracts that later disappeared remain
available to the research process.

- Historical symbols: 1,051
- Daily symbol-month archives: 24,412
- Earliest complete monthly archive: 2020-01
- Latest complete monthly archive: 2026-09
- Contracts represented by only one month: 54
- Longest observed archive: 81 months

The generated catalog is stored at
`data/manifests/binance-um-daily-catalog.json` and is intentionally ignored by
Git because the data directory contains reproducible source artifacts.

## Interpretation

This is a source catalog, not a recommended or executable trading universe. It
contains multiple quote assets, multiplier contracts, short-lived contracts,
and markets that will fail history or liquidity gates.

The user does not have Binance trading access. This catalog supplies historical
research breadth only and does not define TrendBot's eventual venue or
executable universe. Any selected candidate must be reconstructed and
paper-tested with an accessible venue's own data and trading rules.

Eligibility will be evaluated independently on every historical day using only
information available before that day's execution:

- sufficient completed daily history;
- lagged median quote volume;
- current and prior valid price observations;
- supported contract and quote conventions;
- data-quality and continuity checks.

No contract will be included or excluded because it survives to the present or
because its eventual return is known.

## Reproducibility and failure handling

- Catalog discovery paginates the archive and queries only daily prefixes.
- Kline and funding files are cached by their immutable archive keys.
- Every requested file receives a ledger record with cached, downloaded,
  missing, or error status, byte count, and SHA-256 hash when present.
- The manifest is written only after complete discovery; partial enumeration is
  not accepted as a valid universe.
