from dataclasses import replace

from oma.acceptance import AcceptanceContext, Evidence
from oma.authority import AuthorityContext, AuthorityRequest, Capability
from oma.commit import AcceptanceSnapshot, CommitState, CommitToken
from oma.identity import IdentityPolicy, StrictSchema
from oma.obligation import ObligationManifest, ObligationSpec
from oma.pipeline import ComposedPipelineInput, evaluate_composed_pipeline
from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.scope import FileTransition, ScopePolicy
from oma.trust import (
    SignedArtifact,
    TemporalHighWater,
    TrustContext,
    TrustRoot,
    TrustRootStatus,
)
from oma.validation import ValidationDecision, canonical_validation_graph, required_closure


def valid_input() -> ComposedPipelineInput:
    obligation_manifest = ObligationManifest(
        obligation_set_id="obligation-set-1",
        obligations=(
            ObligationSpec("obligation-1", "requirement:obligation-1", 1),
        ),
    )
    return ComposedPipelineInput(
        raw_json="{}",
        schema=StrictSchema(
            schema_id="schema:v1",
            schema_version=1,
            required_fields=frozenset(),
        ),
        namespace="subject",
        raw_id="subject-1",
        identity_policy=IdentityPolicy("identity:v1"),
        scope_policy=ScopePolicy(
            scope_policy_id="scope:v1",
            allowed_paths=("src",),
            protected_roles=frozenset({"VERIFIER", "POLICY"}),
            review_roles=frozenset({"CI"}),
        ),
        transitions=(),
        authority_context=AuthorityContext(
            authority_context_id="authority:v1",
            authority_epoch=1,
            now_epoch=1,
            trusted_issuers=frozenset({"root"}),
        ),
        capabilities=(
            Capability(
                capability_id="cap-1",
                issuer="root",
                holder="agent",
                actions=frozenset({"commit"}),
                targets=frozenset({"subject-1"}),
                scopes=frozenset({"repo"}),
                authority_epoch=1,
                not_before_epoch=0,
                expires_epoch=10,
            ),
        ),
        authority_request=AuthorityRequest(
            actor="agent",
            action="commit",
            target="subject-1",
            scope="repo",
            capability_id="cap-1",
        ),
        trust_context=TrustContext(
            temporal_context_id="time:v1",
            current_trust_epoch=1,
            current_authority_epoch=1,
            current_logical_epoch=1,
            current_state_version=1,
            high_water=TemporalHighWater(1, 1, 1, 1),
        ),
        trust_roots=(
            TrustRoot(
                root_id="root",
                trust_epoch=1,
                status=TrustRootStatus.ACTIVE,
                activated_epoch=0,
            ),
        ),
        signed_artifact=SignedArtifact(
            artifact_id="artifact-1",
            issuer_root_id="root",
            trust_epoch=1,
            authority_epoch=1,
            logical_epoch=1,
            state_version=1,
            issued_epoch=0,
            expires_epoch=10,
        ),
        acceptance_context=AcceptanceContext(
            subject_id="subject-1",
            subject_state_id="state-1",
            verification_context_id="verify-1",
            policy_bundle_id="policy-1",
            required_obligations=frozenset({"obligation-1"}),
        ),
        evidence=(
            Evidence(
                evidence_id="evidence-1",
                obligation_id="obligation-1",
                subject_id="subject-1",
                subject_state_id="state-1",
                verification_context_id="verify-1",
                policy_bundle_id="policy-1",
                passed=True,
            ),
        ),
        retry_policy=RetryPolicy(
            retry_policy_id="retry:v1",
            max_execution_attempts=2,
            max_cumulative_cost=10,
            authorized_retry_reasons=frozenset({"verification_failed"}),
            authorized_recovery_reasons=frozenset({"process_restart"}),
        ),
        retry_domain=RetryDomain(
            retry_domain_id="retry-domain-1",
            subject_id="subject-1",
            pair_id="pair-1",
            lineage_id="lineage-1",
            retry_policy_id="retry:v1",
        ),
        retry_events=(
            RetryEvent(
                event_id="event-1",
                sequence=1,
                kind=RetryEventKind.INITIAL,
                attempt_number=1,
                run_id="run-1",
                subject_id="subject-1",
                pair_id="pair-1",
                lineage_id="lineage-1",
                retry_domain_id="retry-domain-1",
                retry_policy_id="retry:v1",
                reason="initial",
                cost_units=1,
            ),
        ),
        snapshot=AcceptanceSnapshot(
            acceptance_snapshot_id="snapshot-1",
            subject_id="subject-1",
            subject_state_id="state-1",
            policy_bundle_id="policy-1",
            obligation_root="obligation-root-1",
            evidence_root="evidence-root-1",
            ledger_head="ledger-1",
            state_version=1,
            terminal_epoch=1,
        ),
        commit_token=CommitToken(
            token_id="token-1",
            acceptance_snapshot_id="snapshot-1",
            subject_id="subject-1",
            terminal_epoch=1,
        ),
        commit_state=CommitState(
            subject_id="subject-1",
            subject_state_id="state-1",
            policy_bundle_id="policy-1",
            obligation_root="obligation-root-1",
            evidence_root="evidence-root-1",
            ledger_head="ledger-1",
            state_version=1,
            terminal_epoch=1,
        ),
        terminal_commit_id="terminal-1",
        expected_obligation_manifest=obligation_manifest,
        presented_obligation_manifest=obligation_manifest,
    )


def by_node(pipeline_result):
    return {item.node_id: item for item in pipeline_result.observations}


def test_canonical_v3_binds_scope_trust_and_obligation_into_terminal_closure():
    closure = required_closure(canonical_validation_graph())
    assert len(closure) == 15
    assert "scope_integrity" in closure
    assert "trust_temporal" in closure
    assert "obligation_integrity" in closure


def test_pipeline_cannot_accept_while_p0_stages_are_unimplemented():
    result = evaluate_composed_pipeline(valid_input())
    assert result.result.decision is ValidationDecision.NOT_DONE


def test_caller_cannot_supply_validation_observations():
    assert "observations" not in ComposedPipelineInput.__dataclass_fields__


def test_missing_p0_stages_are_explicitly_not_done():
    observations = by_node(evaluate_composed_pipeline(valid_input()))
    missing = {
        "policy_bundle",
        "snapshot_freshness",
        "provenance",
        "aggregation",
        "terminal_barrier",
        "atomic_commit",
    }
    assert {node for node in missing if observations[node].decision is ValidationDecision.NOT_DONE} == missing


def test_valid_obligation_manifest_is_bound_into_pipeline():
    observations = by_node(evaluate_composed_pipeline(valid_input()))
    assert observations["obligation_integrity"].decision is ValidationDecision.ACCEPT


def test_missing_obligation_manifest_is_not_done():
    item = replace(
        valid_input(),
        expected_obligation_manifest=None,
        presented_obligation_manifest=None,
    )
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["obligation_integrity"].decision is ValidationDecision.NOT_DONE


def test_obligation_denominator_reduction_blocks_pipeline():
    item = valid_input()
    item = replace(
        item,
        acceptance_context=replace(
            item.acceptance_context,
            required_obligations=frozenset(),
        ),
        evidence=(),
    )
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK


def test_obligation_substitution_blocks_pipeline():
    item = valid_input()
    presented = ObligationManifest(
        obligation_set_id="obligation-set-1",
        obligations=(ObligationSpec("obligation-1", "evil", 1),),
    )
    item = replace(item, presented_obligation_manifest=presented)
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK


def test_scope_block_precedes_missing_p0_stages():
    item = valid_input()
    item = replace(
        item,
        transitions=(FileTransition("outside/file.py", "a", "b"),),
    )
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK


def test_scope_review_is_not_silently_accepted():
    item = valid_input()
    item = replace(
        item,
        transitions=(
            FileTransition(
                "src/ci.yml",
                "a",
                "b",
                roles=frozenset({"CI"}),
            ),
        ),
    )
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["scope_integrity"].decision is ValidationDecision.NOT_DONE


def test_authority_stale_precedes_not_done():
    item = valid_input()
    item = replace(
        item,
        authority_context=replace(item.authority_context, authority_epoch=2),
    )
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.STALE


def test_trust_stale_precedes_not_done():
    item = valid_input()
    item = replace(
        item,
        trust_context=replace(
            item.trust_context,
            current_trust_epoch=2,
            high_water=TemporalHighWater(2, 1, 1, 1),
        ),
    )
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.STALE


def test_compromised_trust_root_blocks_pipeline():
    item = valid_input()
    item = replace(
        item,
        trust_roots=(
            replace(
                item.trust_roots[0],
                status=TrustRootStatus.COMPROMISED,
                compromised_epoch=1,
            ),
        ),
    )
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK


def test_acceptance_integrity_failure_blocks_pipeline():
    item = valid_input()
    bad_evidence = replace(item.evidence[0], subject_id="other-subject")
    item = replace(item, evidence=(bad_evidence,))
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK


def test_retry_budget_violation_blocks_pipeline():
    item = valid_input()
    item = replace(
        item,
        retry_policy=replace(item.retry_policy, max_cumulative_cost=0),
    )
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK


def test_commit_snapshot_drift_is_stale():
    item = valid_input()
    item = replace(
        item,
        commit_state=replace(item.commit_state, state_version=2),
    )
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.STALE


def test_commit_token_replay_maps_to_global_block():
    item = valid_input()
    item = replace(
        item,
        commit_state=replace(
            item.commit_state,
            consumed_token_ids=frozenset({"token-1"}),
        ),
    )
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK


def test_parse_failure_blocks_pipeline():
    item = replace(valid_input(), raw_json='{"unknown": 1}')
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK


def test_invalid_canonical_identity_blocks_pipeline():
    item = replace(valid_input(), raw_id=" subject-1 ")
    assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK


def test_generated_evidence_roots_are_deterministic():
    first = evaluate_composed_pipeline(valid_input()).observations
    second = evaluate_composed_pipeline(valid_input()).observations
    assert [item.evidence_root for item in first] == [item.evidence_root for item in second]


def test_pipeline_does_not_consume_commit_token_while_not_done():
    item = valid_input()
    evaluate_composed_pipeline(item)
    assert item.commit_state.consumed_token_ids == frozenset()
    assert item.commit_state.terminal_commit_ids == frozenset()
