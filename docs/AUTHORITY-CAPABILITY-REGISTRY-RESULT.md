# Authority Capability Registry — Causal Audit Result

## Attack

The authority authenticity audit demonstrated a real Item 40 failure: a caller could construct a root `Capability` with `issuer="root"`, set `holder="attacker"`, grant commit permission to the real subject, and obtain durable global ACCEPT solely because the issuer string matched `AuthorityContext.trusted_issuers`.

The whole-repository attack run passed 419 tests, including the exploit, proving the behavior was real rather than hypothetical.

## Fix

OMA now has an authoritative SQLite capability registry:

- root capabilities are installed only during trusted context bootstrap;
- context ID, authority epoch and trusted issuer set are digest-bound;
- new post-bootstrap root issuance is forbidden;
- delegated child issuance is validated against the persisted parent chain and subset rules;
- identifiers containing ambiguous newline/NUL storage separators are rejected at the registry boundary;
- executor replaces caller-supplied capabilities with authoritative capabilities when available;
- `SQLiteTerminalStore.commit` re-reads authoritative capabilities inside the same `BEGIN IMMEDIATE` used for terminalization;
- missing authoritative capabilities fail closed.

The caller-supplied `capabilities` tuple is therefore no longer the final authority source at durable terminal commit.

## Whole-repository evidence

PR #7, GitHub Actions CI, run `32299923151`:

```text
CHECKOUT = PASS
PYTHON = 3.12.14
INSTALL = PASS
PYTEST = PASS
TESTS_PASSED = 429
TESTS_FAILED = 0
DURATION = 11.77s
```

## Status delta

```text
ITEM_40_AUTHORITY_CAPABILITY = IMPLEMENTED_INITIAL_ON_DURABLE_LOCAL_BOUNDARY
CALLER_CAPABILITY_SET_FINAL_AUTHORITY = NO
POST_BOOTSTRAP_ROOT_FABRICATION = BLOCKED
DELEGATION_SUBSET_RULES = DURABLY_ENFORCED
```

## Boundary caveat

This does **not** establish cryptographic identity of the trusted root against a hostile process, compromised database, or malicious bootstrap operator. Root key/signature authenticity remains Item 41 and must use standard cryptography/key management if that hostile boundary is required.

## Next causal audit

`TRUST_ARTIFACT_AUTHENTICITY_AUDIT`

Current `SignedArtifact` carries metadata but no signature bytes or cryptographic verification. The next attack tests whether a caller can fabricate an artifact claiming an existing trusted root and thereby satisfy `trust_temporal` and durable terminalization without any issuance proof.
