from dataclasses import replace
import hashlib

from oma.acceptance import AcceptanceContext, Evidence
from oma.authority import AuthorityContext, AuthorityRequest, Capability
from oma.commit import AcceptanceSnapshot, CommitState, CommitToken
from oma.identity import IdentityPolicy, StrictSchema
from oma.obligation import ObligationManifest, ObligationSpec, obligation_root
from oma.pipeline import ComposedPipelineInput, evaluate_composed_pipeline
from oma.provenance import ProvenanceDecision, ProvenanceNode, ProvenancePolicy, evaluate_provenance
from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.scope import FileTransition, ScopePolicy
from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustRoot, TrustRootStatus
from oma.validation import ValidationDecision, canonical_validation_graph, required_closure


def evidence_digest(item: Evidence) -> str:
    payload = "\0".join((item.evidence_id,item.obligation_id,item.subject_id,item.subject_state_id,item.verification_context_id,item.policy_bundle_id,"1" if item.passed else "0")).encode("utf-8")
    return hashlib.sha256(b"oma:evidence:v1\0" + payload).hexdigest()


def valid_input() -> ComposedPipelineInput:
    obligation_manifest = ObligationManifest("obligation-set-1", (ObligationSpec("obligation-1", "requirement:obligation-1", 1),))
    manifest_root = obligation_root(obligation_manifest)
    evidence = Evidence("evidence-1","obligation-1","subject-1","state-1","verify-1","policy-1",True)
    provenance_policy = ProvenancePolicy("prov:v1", frozenset({"prov-root"}), frozenset({"verifier-1"}))
    provenance_nodes = (
        ProvenanceNode("prov-root",frozenset(),"subject-1","state-1","verify-1","policy-1","verifier-1","source-digest"),
        ProvenanceNode("prov-leaf",frozenset({"prov-root"}),"subject-1","state-1","verify-1","policy-1","verifier-1",evidence_digest(evidence),"evidence-1"),
    )
    provenance_result = evaluate_provenance(provenance_policy,provenance_nodes,subject_id="subject-1",subject_state_id="state-1",verification_context_id="verify-1",policy_bundle_id="policy-1",required_evidence_ids=frozenset({"evidence-1"}),required_evidence_digests={"evidence-1": evidence_digest(evidence)})
    assert provenance_result.decision is ProvenanceDecision.ALLOW
    provenance_root = provenance_result.provenance_root
    assert provenance_root is not None
    return ComposedPipelineInput(
        raw_json="{}", schema=StrictSchema("schema:v1",1,frozenset()), namespace="subject", raw_id="subject-1", identity_policy=IdentityPolicy("identity:v1"),
        scope_policy=ScopePolicy("scope:v1",("src",),protected_roles=frozenset({"VERIFIER","POLICY"}),review_roles=frozenset({"CI"})), transitions=(),
        authority_context=AuthorityContext("authority:v1",1,1,frozenset({"root"})), capabilities=(Capability("cap-1","root","agent",frozenset({"commit"}),frozenset({"subject-1"}),frozenset({"repo"}),1,0,10),), authority_request=AuthorityRequest("agent","commit","subject-1","repo","cap-1"),
        trust_context=TrustContext("time:v1",1,1,1,1,TemporalHighWater(1,1,1,1)), trust_roots=(TrustRoot("root",1,TrustRootStatus.ACTIVE,activated_epoch=0),), signed_artifact=SignedArtifact("artifact-1","root",1,1,1,1,0,10),
        acceptance_context=AcceptanceContext("subject-1","state-1","verify-1","policy-1",frozenset({"obligation-1"})), evidence=(evidence,),
        retry_policy=RetryPolicy("retry:v1",2,10,frozenset({"verification_failed"}),frozenset({"process_restart"})), retry_domain=RetryDomain("retry-domain-1","subject-1","pair-1","lineage-1","retry:v1"), retry_events=(RetryEvent("event-1",1,RetryEventKind.INITIAL,1,"run-1","subject-1","pair-1","lineage-1","retry-domain-1","retry:v1","initial",1),),
        snapshot=AcceptanceSnapshot("snapshot-1","subject-1","state-1","policy-1",manifest_root,provenance_root,"ledger-1",1,1), commit_token=CommitToken("token-1","snapshot-1","subject-1",1), commit_state=CommitState("subject-1","state-1","policy-1",manifest_root,provenance_root,"ledger-1",1,1), terminal_commit_id="terminal-1",
        expected_obligation_manifest=obligation_manifest, presented_obligation_manifest=obligation_manifest, provenance_policy=provenance_policy, provenance_nodes=provenance_nodes,
    )


def by_node(pipeline_result): return {item.node_id:item for item in pipeline_result.observations}

def test_canonical_v3_binds_scope_trust_obligation_and_provenance_into_terminal_closure():
    closure=required_closure(canonical_validation_graph()); assert len(closure)==15; assert {"scope_integrity","trust_temporal","obligation_integrity","provenance"} <= closure

def test_pipeline_cannot_accept_while_remaining_p0_stages_are_unimplemented(): assert evaluate_composed_pipeline(valid_input()).result.decision is ValidationDecision.NOT_DONE

def test_caller_cannot_supply_validation_observations(): assert "observations" not in ComposedPipelineInput.__dataclass_fields__

def test_remaining_p0_stages_are_explicitly_not_done():
    observations=by_node(evaluate_composed_pipeline(valid_input())); missing={"policy_bundle","aggregation","terminal_barrier","atomic_commit"}; assert {n for n in missing if observations[n].decision is ValidationDecision.NOT_DONE}==missing; assert observations["snapshot_freshness"].decision is ValidationDecision.ACCEPT

def test_valid_provenance_is_bound_into_pipeline(): assert by_node(evaluate_composed_pipeline(valid_input()))["provenance"].decision is ValidationDecision.ACCEPT

def test_missing_provenance_is_not_done(): assert by_node(evaluate_composed_pipeline(replace(valid_input(),provenance_policy=None,provenance_nodes=None)))["provenance"].decision is ValidationDecision.NOT_DONE

def test_revoked_provenance_blocks_pipeline():
    item=valid_input(); policy=replace(item.provenance_policy,revoked_node_ids=frozenset({"prov-leaf"})); assert evaluate_composed_pipeline(replace(item,provenance_policy=policy)).result.decision is ValidationDecision.BLOCK

def test_provenance_evidence_payload_substitution_blocks_pipeline():
    item=valid_input(); assert evaluate_composed_pipeline(replace(item,evidence=(replace(item.evidence[0],passed=False),))).result.decision is ValidationDecision.BLOCK

def test_snapshot_provenance_root_mismatch_blocks_pipeline():
    item=valid_input(); item=replace(item,snapshot=replace(item.snapshot,evidence_root="wrong-root"),commit_state=replace(item.commit_state,evidence_root="wrong-root")); assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK

def test_valid_obligation_manifest_is_bound_into_pipeline(): assert by_node(evaluate_composed_pipeline(valid_input()))["obligation_integrity"].decision is ValidationDecision.ACCEPT

def test_missing_obligation_manifest_is_not_done(): assert by_node(evaluate_composed_pipeline(replace(valid_input(),expected_obligation_manifest=None,presented_obligation_manifest=None)))["obligation_integrity"].decision is ValidationDecision.NOT_DONE

def test_obligation_denominator_reduction_blocks_pipeline():
    item=valid_input(); assert evaluate_composed_pipeline(replace(item,acceptance_context=replace(item.acceptance_context,required_obligations=frozenset()),evidence=())).result.decision is ValidationDecision.BLOCK

def test_obligation_substitution_blocks_pipeline():
    item=valid_input(); presented=ObligationManifest("obligation-set-1",(ObligationSpec("obligation-1","evil",1),)); assert evaluate_composed_pipeline(replace(item,presented_obligation_manifest=presented)).result.decision is ValidationDecision.BLOCK

def test_snapshot_obligation_root_mismatch_blocks_pipeline():
    item=valid_input(); item=replace(item,snapshot=replace(item.snapshot,obligation_root="wrong-root"),commit_state=replace(item.commit_state,obligation_root="wrong-root")); assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK

def test_scope_block_precedes_missing_p0_stages(): assert evaluate_composed_pipeline(replace(valid_input(),transitions=(FileTransition("outside/file.py","a","b"),))).result.decision is ValidationDecision.BLOCK

def test_scope_review_is_not_silently_accepted(): assert by_node(evaluate_composed_pipeline(replace(valid_input(),transitions=(FileTransition("src/ci.yml","a","b",roles=frozenset({"CI"})),))))["scope_integrity"].decision is ValidationDecision.NOT_DONE

def test_authority_stale_precedes_not_done():
    item=valid_input(); assert evaluate_composed_pipeline(replace(item,authority_context=replace(item.authority_context,authority_epoch=2))).result.decision is ValidationDecision.STALE

def test_trust_stale_precedes_not_done():
    item=valid_input(); item=replace(item,trust_context=replace(item.trust_context,current_trust_epoch=2,high_water=TemporalHighWater(2,1,1,1))); assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.STALE

def test_compromised_trust_root_blocks_pipeline():
    item=valid_input(); item=replace(item,trust_roots=(replace(item.trust_roots[0],status=TrustRootStatus.COMPROMISED,compromised_epoch=1),)); assert evaluate_composed_pipeline(item).result.decision is ValidationDecision.BLOCK

def test_acceptance_integrity_failure_blocks_pipeline():
    item=valid_input(); assert evaluate_composed_pipeline(replace(item,evidence=(replace(item.evidence[0],subject_id="other-subject"),))).result.decision is ValidationDecision.BLOCK

def test_retry_budget_violation_blocks_pipeline():
    item=valid_input(); assert evaluate_composed_pipeline(replace(item,retry_policy=replace(item.retry_policy,max_cumulative_cost=0))).result.decision is ValidationDecision.BLOCK

def test_commit_snapshot_drift_is_stale():
    item=valid_input(); assert evaluate_composed_pipeline(replace(item,commit_state=replace(item.commit_state,state_version=2))).result.decision is ValidationDecision.STALE

def test_commit_token_replay_maps_to_global_block():
    item=valid_input(); assert evaluate_composed_pipeline(replace(item,commit_state=replace(item.commit_state,consumed_token_ids=frozenset({"token-1"})))).result.decision is ValidationDecision.BLOCK

def test_parse_failure_blocks_pipeline(): assert evaluate_composed_pipeline(replace(valid_input(),raw_json='{"unknown": 1}')).result.decision is ValidationDecision.BLOCK

def test_invalid_canonical_identity_blocks_pipeline(): assert evaluate_composed_pipeline(replace(valid_input(),raw_id=" subject-1 ")).result.decision is ValidationDecision.BLOCK

def test_generated_evidence_roots_are_deterministic():
    first=evaluate_composed_pipeline(valid_input()).observations; second=evaluate_composed_pipeline(valid_input()).observations; assert [x.evidence_root for x in first]==[x.evidence_root for x in second]

def test_pipeline_does_not_consume_commit_token_while_not_done():
    item=valid_input(); evaluate_composed_pipeline(item); assert item.commit_state.consumed_token_ids==frozenset(); assert item.commit_state.terminal_commit_ids==frozenset()
