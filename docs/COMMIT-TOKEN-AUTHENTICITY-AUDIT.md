# Commit Token Issuance / Authenticity Audit

Baseline: `80d498c565e641307e9fd8be88644edc3328eaf7`

## Question

Can a freely constructible `CommitToken` create a new acceptance path that bypasses the authority or terminal-closure properties already enforced by OMA?

## Finding

Current `CommitToken` is structurally bound to:

- `acceptance_snapshot_id`
- `subject_id`
- `terminal_epoch`
- `single_use`

and its `token_id` is durably unique. It has no issuer, signature, MAC, or durable issuance record.

Adversarial tests establish the supported semantics:

1. A caller-chosen fresh `token_id` can commit when every authority, evidence, policy, freshness, terminal and durable prerequisite already accepts.
2. The same caller-chosen token cannot replace a failed authority gate.
3. The same caller-chosen token cannot replace a blocked terminal barrier.

Therefore the token currently acts as a **snapshot-bound single-use nonce / replay key**, not as an authority-bearing credential.

## Causal decision

`COMMIT_TOKEN_AUTHENTICITY_BYPASS = NOT_OBSERVED`

Adding a separate cryptographic token issuer now would duplicate authority semantics without closing an observed acceptance bypass. Authority authenticity itself remains a separate PARTIAL boundary because capabilities/trust are not yet cryptographically authenticated.

No production issuer module is added in this work unit.

## Architectural clarification

Security authority remains in the authority/capability + policy + terminal closure chain. The commit token provides replay/uniqueness semantics at the durable boundary.

If a future requirement makes commit tokens independently authority-bearing, issuance/authenticity must then be implemented and modeled explicitly rather than inferred from `token_id` secrecy.

## Regression tests

`tests/test_commit_token_authenticity.py` covers:

- caller-chosen token under otherwise valid authority;
- forged token with failed authority;
- forged token with blocked terminal barrier.

## Next causal target

`DURABLE_RETRY_LEDGER_AUDIT`

The retry validator currently checks a caller-supplied event tuple. The next attack should test whether omitting or rewriting historical retry/cost events can create an acceptance path that would be blocked if the history were authoritative.
