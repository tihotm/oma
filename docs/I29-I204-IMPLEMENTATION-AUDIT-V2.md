# I29-I204 Implementation Audit V2

Audit baseline after P0 architectural fill-in: `1adfcf37819448504bf1a8102bcb250d740f6d7b`.
Audit fix-forward HEAD: `99f19a640ee3b917e6c3c725d987c9821debb329`.

This audit re-evaluates the integrated OMA after obligation, provenance, aggregation, policy bundle, terminal barrier, snapshot freshness, composed execution, and SQLite terminal commit were implemented. It preserves the original audit as historical evidence and does not claim benchmark execution or a fresh full-suite pass.

## Status vocabulary

- `IMPLEMENTED_INITIAL`: real integrated mechanism exists and enforces the intended property in the supported trust boundary.
- `PARTIAL`: substantial real code exists, but an important causal input remains caller-supplied, unbound, non-authoritative, non-durable, or outside the atomic boundary.
- `CONTRADICTED`: current code exposes a path that violates the modeled property.
- `MISSING`: no meaningful implementation exists.

## Audit V2 headline

The original horizontal P0 gaps are no longer missing. OMA now has a real composed pipeline and a durable SQLite terminal path. However, global `IMPLEMENTATION_CONFIRMED` is still blocked by authoritative-state and durable-proof gaps.

During this audit a concrete contradiction was found:

`SQLiteTerminalStore.commit(snapshot, token, current, ...)` could be called directly and durably commit without authority, provenance, aggregation, policy-bundle or terminal-barrier evaluation.

This was fixed forward in:

- `d9080e4` — durable store public commit now receives the full `ComposedPipelineInput` and independently re-evaluates the composed closure;
- `19cf535` — `execute_composed_pipeline` routes through that guarded boundary;
- `99f19a6` — tests separate the guarded public boundary from the private SQL storage primitive and add incomplete-closure rejection coverage.

The low-level `_commit_prevalidated` method is intentionally private and is not a security boundary against arbitrary Python code executing in the same process.

## Item-level matrix

| Item | Topic | V2 status | Current evidence | Remaining gap |
|---|---|---|---|---|
| 29 | Scope-control integrity | PARTIAL | `scope.py`, composed pipeline | `FileTransition.roles` and `touched` remain caller-supplied; no authoritative workspace transition/role source |
| 30 | Provenance completeness / laundering | IMPLEMENTED_INITIAL | `provenance.py`, snapshot evidence-root binding, pipeline | trusted verifier/root sets are configuration objects rather than cryptographically authenticated identities |
| 31 | Aggregation / evidence selection | IMPLEMENTED_INITIAL | `aggregation.py`, expected set, pair/run binding, policy bundle | policy precommit timing is not durably timestamped; expected set originates from caller/configuration |
| 32 | Retry / recovery causal integrity | PARTIAL | `retry.py`, pipeline pair/run binding | retry event history remains supplied as an in-memory tuple; no authoritative durable retry/cost ledger |
| 33 | Termination / false-DONE | IMPLEMENTED_INITIAL | `terminal.py`, canonical terminal policy, pipeline | terminal barrier root is computed but currently discarded by pipeline observation construction and not persisted in terminal record |
| 34 | Obligation-set integrity | IMPLEMENTED_INITIAL | `obligation.py`, obligation root bound to snapshot | expected manifest issuance/history is not durably authoritative |
| 35 | Policy composition | IMPLEMENTED_INITIAL | `policy.py`, 10 policy kinds, bundle root bound to snapshot/current | expected policy bundle is supplied/configured rather than signed/durably issued |
| 36 | TOCTOU / snapshot consistency | PARTIAL | `snapshot.py`, commit CAS checks, SQLite terminal transaction | `CommitState` is still supplied by caller; SQLite does not own/read the authoritative current subject state in the same transaction |
| 37 | Commit replay / duplicate finalization | IMPLEMENTED_INITIAL | SQLite `UNIQUE(token_id)` and `UNIQUE(subject_id, terminal_epoch)`, concurrency test | commit token issuance/authenticity is not implemented; token object can be constructed by caller |
| 38 | Crash/restart durability | IMPLEMENTED_INITIAL | WAL + FULL synchronous; process-exit rollback and committed reopen tests | evidence covers process crash/reopen, not physical power loss/filesystem corruption |
| 39 | Recovery reconciliation / exactly-once effects | PARTIAL | atomic terminal row, `durability.py` model | ledger/provenance/external effects are not written in the same SQLite transaction; old phase model is not integrated with real effect stores |
| 40 | Authority/capability integrity | PARTIAL | `authority.py`, pipeline | capabilities are not cryptographically bound to trust roots; actions/targets/scopes remain free strings |
| 41 | Trust-root rotation / compromise | PARTIAL | `trust.py` | no real signature verification, key material, durable revocation/trust-root store |
| 42 | Clock/epoch/freshness | PARTIAL | trust temporal gate + snapshot monotonicity | temporal high-water remains caller-supplied rather than durably monotonic/authoritative |
| 43 | Identity/canonicalization | PARTIAL | `identity.py` typed canonical identity | most other modules still carry raw string identifiers instead of consuming typed identity values |
| 44 | Namespace/object confusion | PARTIAL | namespace-aware identity digest | cross-module object IDs are not typed-by-construction; namespace enforcement is not universal |
| 45 | Serialization/parser ambiguity | PARTIAL | strict JSON ingress for `raw_json` | acceptance-critical Python objects can be instantiated directly; parser/schema is not mandatory ingress for all structures |
| 46 | Validation-order/dependency integrity | PARTIAL | composed pipeline internally produces observations; terminal barrier exact prerequisite set | `ValidationResult.validation_closure_root` remains only the sorted node-id tuple; generic observation roots do not bind every gate-specific root/context |
| 47 | End-to-end adversarial composition | IMPLEMENTED_INITIAL | `pipeline.py`, `execution.py`, guarded SQLite commit path | authoritative current-state source and full durable closure/effect proof remain unresolved |

## P0/P1 findings after architectural fill-in

### P0-A — durable commit bypass — FIXED FOR PUBLIC CONTRACT

Found during V2: direct public store commit bypassed the composed security chain.

Fix-forward: public `SQLiteTerminalStore.commit` now accepts a complete pipeline input and independently evaluates all pre-atomic observations before SQL commit. An incomplete, stale, or blocked closure cannot reach the transaction through the supported public API.

This closes the accidental/API-level bypass. It is not intended as isolation from malicious Python code running inside the same interpreter and deliberately calling private methods or monkey-patching modules.

### P0-B — authoritative current state — OPEN

`AcceptanceSnapshot` is compared to `CommitState`, but `CommitState` comes from the caller. The terminal SQLite transaction serializes competing terminal writers, but it does not read an authoritative subject-state row owned by OMA.

Attack shape:

1. verification produces snapshot S at state version N;
2. real application/workspace state advances to N+1;
3. caller supplies an old `CommitState` that still equals S;
4. OMA freshness and commit gates see equality and can authorize terminalization.

Required fix direction: introduce an authoritative subject-state source/adapter with version/root CAS and have the final transaction compare the snapshot to that authoritative state, not to a caller-authored `CommitState`.

### P0-C — durable closure proof — OPEN

`TerminalResult.terminal_barrier_root` correctly hashes termination policy + requested action + every prerequisite observation and evidence root. However `pipeline.py` currently discards that root when creating the `terminal_barrier` `ValidationObservation`; it generates a generic hash from node/decision/reasons instead.

The SQLite terminal row also does not persist:

- terminal barrier root;
- validation graph id/version;
- cryptographic validation closure root.

The durable record therefore proves snapshot/token/terminal uniqueness, but not the exact validation closure that authorized it.

Required fix direction: propagate gate-specific roots into observations, persist terminal barrier/closure identity in the atomic terminal row, and make the committed record self-auditable.

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
PROCESS_CRASH_SQLITE_DURABILITY = EXECUTED_PASS_BEFORE_V2_FIX_FORWARD
PUBLIC_DURABLE_COMMIT_BYPASS = FOUND_AND_FIXED_FORWARD
AUTHORITATIVE_CURRENT_STATE = NO
DURABLE_VALIDATION_CLOSURE_PROOF = NO
I29_I204_GLOBAL_IMPLEMENTATION_CONFIRMED = NO
FRESH_FULL_CURRENT_SUITE = NOT_EXECUTED
BENCHMARK_EXECUTED = NO
MEASURED_PRODUCT_EFFECT = NO
```

## Test caveat

Before V2 fix-forward, the SQLite durability suite was executed and passed, including crash/reopen and concurrent writer uniqueness. The interface was then hardened in commits `d9080e4`, `19cf535`, and `99f19a6`. The new tests are published, but a fresh whole-repository execution at the V2 fix-forward HEAD has not been observed in this runtime. Do not carry the previous 9/9 result forward as proof that the modified HEAD is fully green.

## Next work units

Do not add new horizontal gates.

Priority order:

1. `AUTHORITATIVE_SUBJECT_STATE_CAS` — eliminate caller-authored current state at final commit boundary.
2. `DURABLE_CLOSURE_PROOF` — propagate/persist terminal barrier and validation closure roots.
3. full-suite clean execution and cross-module adversarial pack.
4. then reassess I29-I204 for promotion; only after that begin benchmark execution.
