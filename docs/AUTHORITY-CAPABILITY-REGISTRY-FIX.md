# Authority Capability Registry Fix

PR #6 originally demonstrated a causal Item 40 failure: a caller could fabricate a root `Capability` whose `issuer` string matched the configured trusted issuer and obtain durable terminal ACCEPT.

## Fix

OMA now uses an authoritative SQLite capability registry at the durable terminal boundary:

- trusted context bootstrap stores root capabilities once;
- post-bootstrap root issuance is forbidden;
- delegated capability issuance is validated against the persisted parent chain and subset rules;
- context identity/authority epoch/trusted issuer set are digest-bound;
- executor substitutes authoritative capabilities when available;
- `SQLiteTerminalStore.commit` re-reads authoritative capabilities inside the same `BEGIN IMMEDIATE` used for terminalization;
- missing authoritative capability state fails closed.

The caller-supplied `capabilities` tuple is no longer the final source of authority at durable commit.

## Trust-boundary statement

This closes capability object fabrication inside the supported local SQLite control-plane boundary. It does **not** claim cryptographic authenticity of the root issuer against a hostile process or compromised database/bootstrap path. Root key/signature authenticity remains an Item 41 trust problem and should use standard cryptography/key management when that boundary is addressed.

## Regression target

The durable registry is initialized with the legitimate capability. A caller then replaces its input with a fabricated capability claiming `issuer="root"`, `holder="attacker"` and commit permission. The executor/store must use the registered capability set, causing the attacker request to BLOCK and write zero terminal rows.

This PR reruns the whole repository suite against the fix.
