# I29-I204 Implementation Audit

Audit baseline: `c9ba678b32ee6cc3a2676307c09e1db88ecbde87`.

This document audits the real `tihotm/oma` production code against the previously TEST_CONFIRMED property model. It does not claim benchmark execution or measured product effect.

## Audit rules

- `IMPLEMENTED_INITIAL`: real code exists and directly enforces a meaningful subset of the item.
- `PARTIAL`: real code exists, but one or more causal guarantees remain caller-supplied, unbound, non-durable, or incomplete.
- `MISSING`: the required mechanism is not implemented in production code.
- Unit-test success is not treated as end-to-end composition evidence.

## Head inventory

Production modules at this baseline:

- `acceptance.py`
- `authority.py`
- `commit.py`
- `durability.py`
- `identity.py`
- `retry.py`
- `scope.py`
- `trust.py`
- `validation.py`

Tests are module-oriented. No dedicated cross-module integration/adversarial composition suite exists at this baseline.

## Item-level gap matrix

| Item | Topic | Status | Real implementation evidence | Main gap |
|---|---|---|---|---|
| 29 | Scope-control integrity | PARTIAL | `scope.py` | semantic roles and `touched` history are caller-supplied; no authoritative transition log or role classifier |
| 30 | Provenance completeness / laundering | MISSING | no provenance validator | no provenance DAG/root, issuer/verifier lineage, replay/revocation validation |
| 31 | Aggregation / evidence selection | MISSING | no aggregation module | no predeclared expected evidence set, selection policy, pair binding, best-of-N prevention across runs |
| 32 | Retry / recovery causal integrity | PARTIAL | `retry.py` | in-memory/event-list validation only; no durable causal ledger or integration with execution/evidence state |
| 33 | Termination / false-DONE | PARTIAL | `acceptance.py`, graph node name only | no real terminal-barrier implementation covering all obligations/recovery/aggregation/evidence stability/epoch |
| 34 | Obligation-set integrity | PARTIAL | `AcceptanceContext.required_obligations` | no `obligation_set_id`, manifest/root, mutation history, downgrade/substitution protection |
| 35 | Policy composition | MISSING | IDs appear in isolated structures | no immutable policy bundle binding scope/aggregation/retry/termination/obligation/verification policies |
| 36 | TOCTOU / snapshot consistency | PARTIAL | `commit.py` | snapshot fields exist, but no durable snapshot capture or storage CAS adapter |
| 37 | Commit replay / duplicate finalization | PARTIAL | `commit.py` | single-use semantics are in-memory; no DB uniqueness/CAS/atomic durable token consumption |
| 38 | Crash/restart durability | PARTIAL | `durability.py` | state machine semantics only; no durable journal/DB and no real process-kill/restart test |
| 39 | Recovery reconciliation / exactly-once | PARTIAL | `durability.py` | deterministic effect IDs exist, but no external effect store/unique constraints/real reconciliation adapter |
| 40 | Authority/capability integrity | PARTIAL | `authority.py` | capability chain is not cryptographically/trust-bound to `trust.py`; roles/action types are free strings |
| 41 | Trust-root rotation / compromise | PARTIAL | `trust.py` | model semantics exist, but no signature verification/key material/revocation store/durable trust history |
| 42 | Clock/epoch/freshness | PARTIAL | `trust.py` | high-water is caller-provided, not durably persisted; no trusted clock/logical-clock source |
| 43 | Identity/canonicalization | PARTIAL | `identity.py` | canonicalization exists, but identifiers elsewhere remain raw strings and are not typed-by-construction |
| 44 | Namespace/object confusion | PARTIAL | `TypedIdentity`, domain-separated digest | production modules do not consistently consume `TypedIdentity`; cross-module namespace enforcement absent |
| 45 | Serialization/parser ambiguity | PARTIAL | strict JSON parser | parser is not the mandatory ingress for all acceptance-critical objects; schema checks only field sets/numbers |
| 46 | Validation-order/dependency integrity | PARTIAL | `validation.py` | graph accepts caller-created observations; node results are not produced/bound by actual gates |
| 47 | End-to-end adversarial composition | MISSING | no composed executor | no single pipeline that executes parse→identity→authority→policy→snapshot→provenance→aggregation→retry→terminal→commit |

## Critical composition defect

`validation.py` validates the graph structure and aggregates `ValidationObservation` values, but an observation is currently just:

- `node_id`
- `decision`
- `evidence_root`

Nothing proves that `decision=ACCEPT` for `authority_capability`, `provenance`, `aggregation`, `terminal_barrier`, or `atomic_commit` was produced by the corresponding trusted mechanism. A caller can fabricate a full set of ACCEPT observations and obtain overall ACCEPT.

Therefore:

`VALIDATION_GRAPH_PRESENT != VALIDATION_PIPELINE_BOUND`

This is the highest-priority implementation gap.

## Missing mechanisms that block global IMPLEMENTATION_CONFIRMED

### P0 — bind the pipeline

1. Introduce a composed validation pipeline that calls the actual gates rather than accepting arbitrary observations.
2. Make validation observations/results unforgeable by construction inside the pipeline (or cryptographically/durably bound later).
3. Define an explicit mapping for non-uniform decisions, especially `ScopeDecision.REVIEW` and `CommitDecision.CONFLICT`.
4. Require the exact validation closure generated by the pipeline before commit authorization.

### P0 — complete acceptance semantics

5. Implement immutable obligation manifest / `obligation_set_id` and root binding.
6. Implement provenance DAG/root validation and verifier lineage.
7. Implement aggregation policy + expected evidence set + pair/run selection rules.
8. Implement a real terminal barrier rather than a graph node label.
9. Implement immutable policy bundle composition and bind all policy IDs/epochs to snapshot/commit.

### P1 — replace caller-supplied truth with authoritative state

10. Scope transition history must come from an authoritative workspace/event source, not a caller boolean.
11. Semantic protected roles must be derived from trusted configuration/code ownership metadata, not caller tags.
12. Temporal high-water marks must be durably persisted and monotonic.
13. Snapshot/token/terminal transaction semantics need a durable storage adapter with uniqueness/CAS/transaction guarantees.
14. Trust roots/capabilities need real signature/key/revocation verification if used across trust boundaries.
15. Acceptance-critical ingress must use the strict parser and typed identity consistently across modules.

## Current scientific status

```text
PROPERTY_MODEL_I29_I204 = TEST_CONFIRMED
REAL_IMPLEMENTATION_EXISTS = YES
ITEMS_29_47_GLOBALLY_IMPLEMENTATION_CONFIRMED = NO
END_TO_END_COMPOSED_PIPELINE = NO
REAL_DURABLE_STORAGE = NO
REAL_PROCESS_CRASH_RECOVERY = NO
BENCHMARK_EXECUTED = NO
MEASURED_PRODUCT_EFFECT = NO
```

## Test-status caveat

Module-level tests were executed during incremental implementation. At this audit point, a clean remote checkout/full-suite rerun could not be completed in the current runtime because direct GitHub DNS/network access for `git clone` was unavailable. The repository contents were inspected through the connected GitHub application instead.

Do not report a fresh full-suite PASS until the current HEAD is re-run in one reproducible checkout/environment.

## Next work unit

Do not add another horizontal security module.

The next unit is **COMPOSED_PIPELINE_BINDING**:

- create one internal pipeline that consumes real typed inputs;
- invokes implemented gates in canonical dependency order;
- removes caller-authored `ValidationObservation` as an acceptance authority;
- leaves currently missing provenance/aggregation/obligation/policy/terminal stages explicitly NOT_DONE rather than faking ACCEPT;
- adds cross-module adversarial tests proving that fabricated stage success cannot reach ACCEPT.
