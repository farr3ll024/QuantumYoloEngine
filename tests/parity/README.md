# Behavioral parity fixtures

Each `fixtures/*.json` file is a self-contained scenario: a strategy, an
ordered list of price ticks, and the exact orders/positions/events/equity
curve/summary the Python reference engine produced for that input.

Regenerate with:

```bash
python tests/parity/generate_fixtures.py
```

## Rounding policy

Every float is rounded to **8 decimal places** (`ROUND_DP` in
`generate_fixtures.py`) before serialization. This matches the base-asset
quantity precision used by the fill logic in `quantum_yolo_engine/engine.py`
and preserves USD values far below a cent. Any engine that wants to
reproduce a fixture (including the TypeScript port under `web/src/engine`)
must round every float to 8 decimal places with the same rounding mode
(Python's `round()`, banker's rounding) before comparing.

## Non-deterministic fields (excluded from exact comparison)

Three kinds of records are stamped with the wall-clock time at which
`PaperTrader.bootstrap()` ran, not a tick timestamp, so they will differ
between two runs of the same scenario:

- the `strategy_loaded` event's `ts` and its `payload.snapshot.generated_at_utc`
- the `bootstrap_position` and `seed_entries` events' `ts`
- `entry`-type orders' `created_at` (they're inserted during bootstrap, before
  any tick has fired)

`tests/python/test_parity_fixtures.py` normalizes these before comparing a
freshly-generated run against the committed fixture, by replacing every
occurrence of the bootstrap timestamp with a fixed placeholder in both
sides. Every other field — all tick-driven event `ts` values, fill prices,
quantities, the equity curve, and the summary — must match exactly.
