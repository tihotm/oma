from oma.provenance import ProvenanceDecision, ProvenanceNode, ProvenancePolicy, evaluate_provenance


def test_v12_17_provenance_digest_mismatch_still_blocks():
    policy = ProvenancePolicy("prov:v1", frozenset({"root"}), frozenset({"verifier"}))
    node = ProvenanceNode("root", frozenset(), "subject:1", "state:1", "verify:1", "bundle:1", "verifier", "actual", "ev:1")
    result = evaluate_provenance(
        policy,
        (node,),
        subject_id="subject:1",
        subject_state_id="state:1",
        verification_context_id="verify:1",
        policy_bundle_id="bundle:1",
        required_evidence_ids=frozenset({"ev:1"}),
        required_evidence_digests={"ev:1": "expected"},
    )
    assert result.decision is ProvenanceDecision.BLOCK
