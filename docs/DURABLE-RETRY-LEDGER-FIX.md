# Durable Retry Ledger Fix

Causal attack baseline: PR #4 demonstrated that a caller could omit historical retry events and reopen durable ACCEPT even though the complete retry history exceeded `max_execution_attempts`.

## Fix

OMA now has an append-only SQLite retry ledger:

- durable retry-domain identity and policy digest;
- monotonic event sequence;
- unique event IDs;
- subject/pair/lineage/policy binding;
- blocked over-limit events remain persisted as factual history;
- executor reads authoritative retry history when available;
- public `SQLiteTerminalStore.commit` re-reads the retry ledger inside the same `BEGIN IMMEDIATE` transaction used for terminalization;
- missing authoritative retry history fails closed.

The caller-supplied `retry_events` tuple is therefore no longer the final source of truth at the durable terminal boundary.

## Regression target

If SQLite contains attempts 1, 2 and 3 under a policy with `max_execution_attempts=2`, a caller presenting only attempt 1 must still receive `retry_recovery=BLOCK`, global `BLOCK`, and zero terminal rows.

## First CI confrontation

The first fix run produced 415 PASS / 1 FAIL. The sole failure was an intentionally valid independent protection: a test changed the authoritative latest run from `run-1` to `run-2` while leaving aggregation/evidence bound to `run-1`, so aggregation correctly blocked.

The fixture was corrected to use a same-run retry when testing only source-of-truth replacement. No production protection was relaxed.

This PR is rerun against that corrected separation of concerns.
