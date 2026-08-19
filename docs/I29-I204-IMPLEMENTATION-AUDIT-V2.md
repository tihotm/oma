# I29-I204 Implementation Audit V2

Audit baseline after P0 architectural fill-in: `1adfcf37819448504bf1a8102bcb250d740f6d7b`.
Audit V2 full-suite evidence: PR #1 merge checkout `4b509354f3ea3f69a1bfec24d5d74d68b86bb668`, 399/399 tests passed on GitHub Actions / Python 3.12.13.
Latest main HEAD after merging the compatibility regression test: `6de7315739213a3ccfbf8d8ab66a7d946ef9e902`.

This audit re-evaluates the integrated OMA after obligation, provenance, aggregation, policy bundle, terminal barrier, snapshot freshness, composed execution, SQLite terminal commit, durable-boundary hardening, authoritative subject-state CAS, and durable validation-closure proof were implemented.

## Status vocabulary

- `IMPLEMENTED_INITIAL`: real integrated mechanism exists and enforces the intended property in the supported trust boundary, with direct tests and/or integrated evidence.
- `PARTIAL`: substantial real code exists, but an important causal input remains caller-supplied, unbound, non-authoritative, non-durable, or outside the atomic boundary.
- `CONTRADICTED`: current supported path exposes a violation of the modeled property.
- `MISSING`: no meaningful implementation exists.

## Audit V2 headline

The original horizontal P0 gaps are no longer missing. OMA now has:

- a composed validation pipeline;
- immutable obligation, provenance, aggregation and policy roots;
- a real false-DONE terminal barrier;
- snapshot freshness / TOCTOU checks;
- an authoritative SQLite subject-state CAS;
- a guarded durable terminal boundary;
- cryptographic validation observation / closure digests;
- terminal rows that persist validation graph id, real terminal-barrier root and precommit closure digest;
- process-level SQLite crash/reopen and competing-writer semantics;
- a fresh full GitHub Actions suite of 399/399 tests.

Three terminal-boundary defects were found and fixed forward during V2:

1. **Durable commit bypass** — the public SQLite store could bypass the composed chain.
2. **Caller-authored current state** — freshness could trust an old caller-supplied `CommitState`.
3. **Non-auditable durable acceptance** — the terminal row did not preserve the exact validation closure that authorized it.

A fourth regression was caught during the closure hardening itself: the Evidence payload digest domain was accidentally changed. Commit `bf1462f` restored compatibility with the established `oma:evidence:v1` provenance identity, and PR #1 added a permanent regression test.

## Fix-forward history

### Durable public-boundary hardening

- `d9080e4` — public store commit receives the full `ComposedPipelineInput` and independently re-evaluates closure.
- `19cf535` — `execute_composed_pipeline` routes through the guarded store boundary.
- `99f19a6` — storage tests separate the private SQL primitive from the guarded public API.

The low-level `_commit_prevalidated` method is intentionally private and is not a security boundary against arbitrary Python code deliberately running inside the same interpreter.

### Authoritative subject-state CAS

- `dfc2564` — SQLite owns `subject_states`, initialization, monotonic CAS updates, and reads authoritative state inside the same `BEGIN IMMEDIATE` used for terminal commit.
- `4ceaa21` — execution evaluates using authoritative state; the store re-reads/re-evaluates it transactionally.
- `f4252d3` — tests cover caller lying with an old matching state after authoritative forward drift, caller fake-newer state, missing authoritative state, and durable execution.
- `99fe93c` — guarded SQLite tests initialize authoritative state explicitly.
- `bb51391` — authoritative state primitives exported.

Supported-path consequence:

`caller CommitState != final source of truth`

The final TOCTOU boundary now uses the SQLite-owned subject row and serializes subject-state comparison with terminal commit.

### Durable validation-closure proof

- `f093851` / `f5a4f85` — cryptographic graph-bound digests over validation observations / full closure.
- `ec51f41` — validation observations bind factual gate inputs/results; native gate roots are propagated when available.
- `ea876ce` — SQLite terminal row persists `validation_graph_id`, `terminal_barrier_root`, and `precommit_closure_digest` in the same transaction as terminalization.
- `bf1462f` — restores historical `oma:evidence:v1` payload digest compatibility after closure refactor.
- `44548bb` — exports validation digest primitives.
- `4da0f1c` — tests deterministic graph binding, factual-input sensitivity, terminal root propagation, durable proof persistence and reopen.
- PR #1 / `fdacd93` — evidence-digest regression coverage; full CI succeeded before squash merge.

The durable terminal record is now self-auditable for the supported pre-atomic validation path: graph identity, real terminal barrier and the deterministic precommit observation set are persisted together with snapshot/token/state roots.

## Item-level matrix

| Item | Topic | V2 status | Current evidence | Remaining gap |
|---|---|---|---|---|
| 29 | Scope-control integrity | PARTIAL | `scope.py`, composed pipeline | `FileTransition.roles` and `touched` remain caller-supplied; no authoritative workspace transition/role source |
| 30 | Provenance completeness / laundering | IMPLEMENTED_INITIAL | `provenance.py`, native provenance root propagated into validation closure | trusted verifier/root sets are configuration objects rather than cryptographically authenticated identities |
| 31 | Aggregation / evidence selection | IMPLEMENTED_INITIAL | expected set + pair/run binding + native aggregation root in closure | expected-set issuance/precommit timing is configured, not durably timestamped |
| 32 | Retry / recovery causal integrity | PARTIAL | `retry.py`, pipeline pair/run binding | retry event/cost history remains supplied as an in-memory tuple; no authoritative durable retry ledger |
| 33 | Termination / false-DONE | IMPLEMENTED_INITIAL | canonical terminal policy; real `terminal_barrier_root` propagated and persisted | external effects after terminalization still require atomic/outbox semantics |
| 34 | Obligation-set integrity | IMPLEMENTED_INITIAL | obligation manifest/root bound to snapshot and closure | expected manifest issuance/history is not durably authoritative |
| 35 | Policy composition | IMPLEMENTED_INITIAL | 10 policy kinds; policy bundle root bound to snapshot/current and closure | expected policy bundle is configured rather than signed/durably issued |
| 36 | TOCTOU / snapshot consistency | IMPLEMENTED_INITIAL | SQLite `subject_states`; same-transaction authoritative read + terminal write | external workspace/application state must be adapted into this CAS to inherit the guarantee |
| 37 | Commit replay / duplicate finalization | IMPLEMENTED_INITIAL | SQLite `UNIQUE(token_id)` + `UNIQUE(subject_id, terminal_epoch)` + competing-writer tests | commit-token issuance/authenticity is not implemented; matching tokens remain constructible by caller |
| 38 | Crash/restart durability | IMPLEMENTED_INITIAL | WAL + FULL synchronous; process-exit rollback/commit-reopen coverage; full suite green | no claim for physical power loss/filesystem corruption beyond SQLite/OS guarantees tested here |
| 39 | Recovery reconciliation / exactly-once effects | PARTIAL | atomic terminal row; durable proof; `durability.py` semantic model | ledger/provenance/external effects are not all committed through the same transaction/outbox |
| 40 | Authority/capability integrity | PARTIAL | `authority.py`, factual authority observation bound into closure | capabilities are not cryptographically bound to trust roots; action/target/scope remain free strings |
| 41 | Trust-root rotation / compromise | PARTIAL | `trust.py`, factual trust observation bound into closure | no real signature verification, key material, durable revocation/trust-root store |
| 42 | Clock/epoch/freshness | PARTIAL | trust temporal gate + authoritative state monotonicity | trust temporal high-water remains supplied rather than durably monotonic/authoritative |
| 43 | Identity/canonicalization | PARTIAL | typed canonical identity + identity observation factual binding | most cross-module IDs still use raw strings instead of typed identity values |
| 44 | Namespace/object confusion | PARTIAL | namespace-aware identity digest | namespace/type enforcement is not universal across cross-module objects |
| 45 | Serialization/parser ambiguity | PARTIAL | strict JSON ingress; parse observation binds raw payload + schema | acceptance-critical Python objects can still be instantiated directly; parser is not universal ingress |
| 46 | Validation-order/dependency integrity | IMPLEMENTED_INITIAL | internal composed observations; graph dependency checks; cryptographic closure digest; durable precommit proof | generic validation primitives are not isolation from malicious code inside the same interpreter |
| 47 | End-to-end adversarial composition | IMPLEMENTED_INITIAL | composed evaluator + guarded executor + authoritative CAS + durable closure proof + 399-test CI | remaining limitations are the P1 trust/ledger/typed-ingress boundaries below, not a missing composed path |

## Full-suite evidence

GitHub Actions workflow `CI`, PR #1, run `32291665157`, job `96193648515`:

```text
CHECKOUT = PASS
PYTHON = 3.12.13
INSTALL = PASS
PYTEST = PASS
TESTS_PASSED = 399
TESTS_FAILED = 0
DURATION = 1.35s
```

The workflow checked out GitHub's PR merge commit `4b509354f3ea3f69a1bfec24d5d74d68b86bb668`, which combined main `4da0f1ce4bbf566786a70c06c0f57242ca7b906c` with the evidence-digest compatibility test `fdacd938dd983f41d4736a654f6376dca1bdba29`. PR #1 then squash-merged that test into main as `6de7315739213a3ccfbf8d8ab66a7d946ef9e902`.

This is a real whole-repository suite result, not a sum of isolated module runs.

## Remaining P1 gaps

No new horizontal gate should be added without a causal failure class. The current highest-value hardening targets are:

1. **Commit-token issuance/authenticity** — tokens are single-use durably but are still freely constructible data objects.
2. **Durable retry/cost ledger** — causal attempts/cost are validated but not sourced from an authoritative durable ledger.
3. **Authoritative scope transition source** — `roles` and `touched` must eventually come from the workspace/change engine, not the caller.
4. **Durable temporal high-water / trust roots** — trust rollback checks need durable monotonic state and, for hostile boundaries, real signatures/keys/revocation.
5. **Terminal effects/outbox** — external ledger/provenance/side effects need same-transaction or durable outbox/idempotent reconciliation semantics.
6. **Typed identity + strict serialization expansion** — reduce raw-string/object construction paths at trust boundaries.

## Scientific status after Audit V2

```text
PROPERTY_MODEL_I29_I204 = TEST_CONFIRMED
REAL_IMPLEMENTATION_EXISTS = YES
COMPOSED_PIPELINE_EXISTS = YES
DURABLE_SQLITE_TERMINAL_PATH_EXISTS = YES
PUBLIC_DURABLE_COMMIT_BYPASS = FOUND_AND_FIXED_FORWARD
AUTHORITATIVE_SUBJECT_STATE_CAS = IMPLEMENTED_INITIAL
DURABLE_VALIDATION_CLOSURE_PROOF = IMPLEMENTED_INITIAL
FRESH_FULL_REPOSITORY_SUITE = PASS_399_OF_399
I29_I204_ALL_ITEMS_IMPLEMENTED = NO
I29_I204_GLOBAL_IMPLEMENTATION_CONFIRMED = NO
BENCHMARK_EXECUTED = NO
MEASURED_PRODUCT_EFFECT = NO
```

`GLOBAL_IMPLEMENTATION_CONFIRMED = NO` remains intentional: items 29, 32, 39-45 still have explicit partial boundaries. A green suite proves the implemented contracts; it does not prove properties the code does not yet claim to implement.

## Next work unit

Do not start benchmark yet.

Next: `COMMIT_TOKEN_ISSUANCE_AUTHENTICITY_AUDIT` — first adversarially prove whether freely constructible `CommitToken` can create a new acceptance path that bypasses any intended authority/closure property. Only then implement the minimal issuance mechanism if the attack is causally real.
