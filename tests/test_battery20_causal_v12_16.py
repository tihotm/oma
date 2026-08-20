from oma.provenance import ProvenanceDecision, ProvenanceNode, ProvenancePolicy, evaluate_provenance


def evaluate(subject_id, subject_state_id):
    policy = ProvenancePolicy("prov:v1", frozenset({"root"}), frozenset({"verifier"}))
    node = ProvenanceNode(
        node_id="root",
        parent_ids=frozenset(),
        subject_id=subject_id,
        subject_state_id=subject_state_id,
        verification_context_id="verify:1",
        policy_bundle_id="bundle:1",
        verifier_id="verifier",
        payload_digest="digest:1",
        evidence_id="ev:1",
    )
    return evaluate_provenance(
        policy,
        (node,),
        subject_id=subject_id,
        subject_state_id=subject_state_id,
        verification_context_id="verify:1",
        policy_bundle_id="bundle:1",
        required_evidence_ids=frozenset({"ev:1"}),
        required_evidence_digests={"ev:1": "digest:1"},
    )


def test_v12_16_valid_provenance_inputs_can_collide_across_subject_state_boundary():
    left = evaluate("a", "b\0c")
    right = evaluate("a\0b", "c")
    assert left.decision is ProvenanceDecision.ALLOW
    assert right.decision is ProvenanceDecision.ALLOW
    assert left.provenance_root == right.provenance_root
