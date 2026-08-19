# Durable Retry Ledger — Causal Audit Result

## Attack

PR #4 demonstrated a real supported-path failure: a caller could present only the initial retry event even when the factual history contained a third execution attempt that exceeded `max_execution_attempts=2`.

Before the fix:

- complete history -> `retry_recovery=BLOCK`;
- caller-truncated history -> durable global `ACCEPT`.

Therefore the in-memory `retry_events` tuple was causally insufficient as a terminal source of truth.

## Fix

OMA now has an append-only SQLite retry ledger with:

- durable retry-domain identity;
- retry-policy digest binding;
- monotonic sequence;
- unique event IDs;
- subject/pair/lineage/policy binding;
- factual persistence even when a newly appended event makes the domain exceed retry/budget policy;
- fail-closed missing authoritative history;
- executor replacement of caller-supplied history with authoritative history when available;
- transactional re-read by `SQLiteTerminalStore.commit` inside the same `BEGIN IMMEDIATE` used for terminalization.

The durable store, not the caller tuple, is now the final source of retry/cost history at terminal commit.

## Regression

With attempts 1, 2 and 3 persisted under `max_execution_attempts=2`, a caller presenting only attempt 1 still receives `retry_recovery=BLOCK`, global `BLOCK`, and zero terminal rows.

## Whole-repository evidence

PR #5, GitHub Actions CI, run `32299032413`:

```text
CHECKOUT = PASS
PYTHON = 3.12.13
INSTALL = PASS
PYTEST = PASS
TESTS_PASSED = 416
TESTS_FAILED = 0
DURATION = 1.47s
```

The first fix run had 415 PASS / 1 FAIL because a source-of-truth test changed the authoritative latest run to `run-2` while aggregation/evidence remained bound to `run-1`; aggregation correctly blocked. The fixture was corrected to isolate retry-history authority without weakening production behavior.

## Status delta

```text
ITEM_32_RETRY_RECOVERY = IMPLEMENTED_INITIAL
CALLER_RETRY_HISTORY_FINAL_AUTHORITY = NO
DURABLE_RETRY_LEDGER = YES
RETRY_HISTORY_OMISSION_ATTACK = CLOSED_ON_DURABLE_PATH
```

Remaining caveat: the component that appends factual retry events must itself be integrated with the real execution runtime so executed work cannot occur without ledger recording. The terminal boundary is fail-closed against missing or rewritten durable history once recorded.

## Next causal audit

`AUTHORITY_CAPABILITY_AUTHENTICITY_AUDIT`

Test whether a caller can fabricate a capability claiming a trusted issuer and thereby obtain `authority_capability=ACCEPT` without any authenticated issuance proof.
