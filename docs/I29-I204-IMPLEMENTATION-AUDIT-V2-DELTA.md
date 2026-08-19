# I29-I204 Implementation Audit V2 — Outcome Proof Delta

Baseline: `9bb12639b169b3ab818bc0872536af7add26bc1f`.

This delta records one additional system-level defect found after Audit V2 and its fix-forward.

## Defect found

The durable SQLite boundary correctly enforced token replay and `(subject_id, terminal_epoch)` uniqueness, but the final `atomic_commit` validation observation was derived only from decision/reasons. Therefore two distinct durable outcomes with the same precommit facts but different `token_id` / `terminal_commit_id` could share the same atomic observation root and final validation-closure digest.

This did **not** permit duplicate finalization in the same durable store. It was an auditability / exactly-once proof-identity defect: the final proof did not cryptographically identify the concrete durable outcome that had been committed.

Affected modeled areas: Item 37 (replay / duplicate finalization proof identity) and Item 39 (exactly-once outcome / recovery auditability).

## Fix-forward

- `64ae34e6efefaa6d311ac69ba6e14ff237328785` — bind `acceptance_snapshot_id`, `token_id`, and concrete `terminal_commit_id` into the `atomic_commit` evidence root using length-prefixed encoding.
- `9bb12639b169b3ab818bc0872536af7add26bc1f` — add regression tests proving:
  - distinct durable outcome identities produce different atomic roots and different final closure digests;
  - identical durable outcome identities remain deterministic across independent stores.

## Current interpretation

Item 37 remains `IMPLEMENTED_INITIAL`: durable uniqueness was already real; final proof identity is now also bound to the concrete outcome.

Item 39 remains `PARTIAL`: terminal outcome identity is now cryptographically represented in the final closure, but external ledger/provenance/application effects still require same-transaction or durable outbox/idempotent reconciliation semantics.

## Evidence discipline

The historical Audit V2 full-suite evidence remains 399/399 at its recorded PR merge checkout. The two new regression tests in this delta must not be counted as whole-suite PASS until a fresh CI run completes on a commit containing this delta and the outcome-identity fix.
