# I29-I204 Implementation Audit V2

Audit baseline after P0 architectural fill-in: `1adfcf37819448504bf1a8102bcb250d740f6d7b`.
Latest fix-forward HEAD covered by this document: `bb51391588c6b06f8df47dd5d9845e56f9423834`.

This audit re-evaluates the integrated OMA after obligation, provenance, aggregation, policy bundle, terminal barrier, snapshot freshness, composed execution, SQLite terminal commit, durable-boundary hardening, and authoritative subject-state CAS were implemented. It preserves the original audit as historical evidence and does not claim benchmark execution or a fresh full-suite pass.

## Status vocabulary

- `IMPLEMENTED_INITIAL`: real integrated mechanism exists and enforces the intended property in the supported trust boundary.
- `PARTIAL`: substantial real code exists, but an important causal input remains caller-supplied, unbound, non-authoritative, non-durable, or outside the atomic boundary.
- `CONTRADICTED`: current supported path exposes a violation of the modeled property.
- `MISSING`: no meaningful implementation exists.

## Audit V2 headline

The original horizontal P0 gaps are no longer missing. OMA now has a composed validation pipeline, an authoritative SQLite subject-state CAS, and a durable terminal commit path.

Two concrete terminal-boundary defects were found and fixed forward during this audit:

1. **Durable commit bypass**: the public SQLite store could previously be called with only snapshot/token/current and bypass composed authority/provenance/aggregation/policy/terminal checks.
2. **Caller-authored current state**: freshness/commit could previously trust a caller-supplied `CommitState`, allowing an old state to be presented after the real subject advanced.

The next highest-priority open gap is durable validation-closure proof.

## Fix-forward history

### Durable public-boundary hardening

- `d9080e4` — public store commit receives the full `ComposedPipelineInput` and independently re-evaluates closure.
- `19cf535` — `execute_composed_pipeline` routes through the guarded store boundary.
- `99f19a6` — storage tests separate the private SQL primitive from the guarded public API.

The low-level `_commit_prevalidated` method is intentionally private and is not a security boundary against arbitrary Python code deliberately running inside the same interpreter.

### Authoritative subject-state CAS

- `dfc2564` — SQLite owns `subject_states`, initialization, monotonic CAS updates, and reads authoritative state inside the same `BEGIN IMMEDIATE` used for terminal commit.
- `4ceaa21` — execution evaluates using the authoritative state when available; the store re-reads/re-evaluates it transactionally.
- `f4252d3` — tests cover caller lying with an old matching state after authoritative forward drift, caller fake-newer state, missing authoritative state, and durable execution.
- `99fe93c` — guarded SQLite tests initialize authoritative state explicitly.
- `bb51391` — authoritative state primitives exported.

Supported-path consequence:

`caller CommitState != final source of truth`

The final TOCTOU boundary now uses the SQLite-owned subject row and serializes subject-state comparison with terminal commit.

## Item-level matrix

| Item | Topic | V2 status | Current evidence | Remaining gap |
|---|---|---|---|---|
| 29 | Scope-control integrity | PARTIAL | `scope.py`, composed pipeline | `FileTransition.roles` and `touched` remain caller-supplied; no authoritative workspace transition/role source |
| 30 | Provenance completeness / laundering | IMPLEMENTED_INITIAL | `provenance.py`, snapshot evidence-root binding, pipeline | trusted verifier/root sets are configuration objects rather than cryptographically authenticated identities |
| 31 | Aggregation / evidence selection | IMPLEMENTED_INITIAL | `aggregation.py`, expected set, pair/run binding, policy bundle | policy precommit timing is not durably timestamped; expected set originates from configured input |
| 32 | Retry / recovery causal integrity | PARTIAL | `retry.py`, pipeline pair/run binding | retry event/cost history remains supplied as an in-memory tuple; no authoritative durable retry ledger |
| 33 | Termination / false-DONE | IMPLEMENTED_INITIAL | `terminal.py`, canonical terminal policy, pipeline | terminal barrier root is computed but currently discarded by pipeline observation construction and not persisted in terminal record |
| 34 | Obligation-set integrity | IMPLEMENTED_INITIAL | `obligation.py`, obligation root bound to snapshot | expected manifest issuance/history is not durably authoritative |
| 35 | Policy composition | IMPLEMENTED_INITIAL | `policy.py`, 10 policy kinds, bundle root bound to snapshot/current | expected policy bundle is configured rather than signed/durably issued |
| 36 | TOCTOU / snapshot consistency | IMPLEMENTED_INITIAL | `snapshot.py`, SQLite `subject_states`, same-transaction authoritative read + terminal write | authoritative guarantee holds only for state changes routed through this SQLite state CAS; external workspace/application state still needs an adapter into it |
| 37 | Commit replay / duplicate finalization | IMPLEMENTED_INITIAL | SQLite `UNIQUE(token_id)` and `UNIQUE(subject_id, terminal_epoch)`, concurrency semantics | commit-token issuance/authenticity is not implemented; token object can be constructed by caller |
| 38 | Crash/restart durability | IMPLEMENTED_INITIAL | WAL + FULL synchronous; process-exit rollback and committed reopen tests before V2 changes | evidence covers process crash/reopen, not physical power loss/filesystem corruption; fresh post-V2 rerun still required |
| 39 | Recovery reconciliation / exactly-once effects | PARTIAL | atomic terminal row, `durability.py` model | ledger/provenance/external effects are not written in the same SQLite transaction; old phase model is not integrated with real effect stores |
| 40 | Authority/capability integrity | PARTIAL | `authority.py`, pipeline | capabilities are not cryptographically bound to trust roots; actions/targets/scopes remain free strings |
| 41 | Trust-root rotation / compromise | PARTIAL | `trust.py` | no real signature verification, key material, durable revocation/trust-root store |
| 42 | Clock/epoch/freshness | PARTIAL | trust temporal gate + snapshot monotonicity | temporal high-water remains caller-supplied rather than durably monotonic/authoritative |
| 43 | Identity/canonicalization | PARTIAL | `identity.py` typed canonical identity | most other modules still carry raw string identifiers instead of consuming typed identity values |
| 44 | Namespace/object confusion | PARTIAL | namespace-aware identity digest | cross-module object IDs are not typed-by-construction; namespace enforcement is not universal |
| 45 | Serialization/parser ambiguity | PARTIAL | strict JSON ingress for `raw_json` | acceptance-critical Python objects can be instantiated directly; parser/schema is not mandatory ingress for all structures |
| 46 | Validation-order/dependency integrity | PARTIAL | composed pipeline internally produces observations; terminal barrier exact prerequisite set; durable store re-evaluates closure | `ValidationResult.validation_closure_root` remains a sorted node-id tuple; generic observation roots do not bind every gate-specific root/context |
| 47 | End-to-end adversarial composition | IMPLEMENTED_INITIAL | `pipeline.py`, `execution.py`, guarded SQLite commit, authoritative subject state | durable exact-closure proof and external-effect atomicity/reconciliation remain unresolved |

## Open P0 — durable closure proof

`TerminalResult.terminal_barrier_root` hashes termination policy + requested action + every prerequisite observation and evidence root. However `pipeline.py` currently discards that gate-specific root when creating the `terminal_barrier` `ValidationObservation`; the observation receives the generic pipeline hash of node/decision/reasons instead.

The SQLite terminal row also does not persist:

- terminal barrier root;
- validation graph id/version;
- cryptographic validation closure root.

Therefore the current durable record proves snapshot/token/state/terminal uniqueness and authoritative-state freshness, but it is not yet a self-contained proof of the exact validation closure that authorized the commit.

Required fix direction:

1. allow `ValidationObservation.evidence_root` to carry the real gate-specific root where one exists (`policy_bundle_root`, `provenance_root`, `obligation_root`, `aggregation_root`, `terminal_barrier_root`);
2. define a cryptographic validation closure root over graph id + ordered node id + decision + evidence root;
3. persist graph id, terminal barrier root, and closure root in the same terminal SQLite row;
4. test root changes when any bound gate evidence changes and survives reopen.

## Important P1 gaps

1. Scope roles and touch history need an authoritative workspace/change source.
2. Retry/cost history needs a durable causal ledger.
3. Temporal high-water needs durable monotonic storage.
4. Token issuance needs an authenticated/controlled issuer rather than a freely constructible dataclass.
5. Trust/capabilities need signatures/keys/revocation if the boundary includes untrusted producers.
6. Typed identity and strict serialization need to become mandatory across acceptance-critical ingress.
7. Ledger/provenance/external terminal effects need either the same transaction or an outbox/reconciliation protocol with durable uniqueness.

## Scientific status at V2

```text
PROPERTY_MODEL_I29_I204 = TEST_CONFIRMED
REAL_IMPLEMENTATION_EXISTS = YES
COMPOSED_PIPELINE_EXISTS = YES
DURABLE_SQLITE_TERMINAL_PATH_EXISTS = YES
PUBLIC_DURABLE_COMMIT_BYPASS = FOUND_AND_FIXED_FORWARD
AUTHORITATIVE_SUBJECT_STATE_CAS = IMPLEMENTED_INITIAL
DURABLE_VALIDATION_CLOSURE_PROOF = NO
I29_I204_GLOBAL_IMPLEMENTATION_CONFIRMED = NO
FRESH_FULL_CURRENT_SUITE = NOT_EXECUTED
BENCHMARK_EXECUTED = NO
MEASURED_PRODUCT_EFFECT = NO
```

## Test caveat

Before V2 fix-forward, SQLite durability tests were executed successfully, including crash/reopen and concurrent writer uniqueness. The durable API and authoritative-state path were modified after those runs. The new tests are published, but a fresh whole-repository execution at the latest fix-forward HEAD has not been observed in this runtime. Do not carry the earlier 9/9 result forward as proof that the modified HEAD is fully green.

## Next work units

Do not add new horizontal gates.

Priority order:

1. `DURABLE_CLOSURE_PROOF` — propagate/persist gate roots and a cryptographic validation closure root.
2. full-suite clean execution and cross-module adversarial pack.
3. then reassess I29-I204 for promotion; only after that begin benchmark execution.
