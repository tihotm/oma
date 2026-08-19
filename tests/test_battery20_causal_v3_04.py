from oma.provenance import ProvenanceDecision, ProvenanceNode, ProvenancePolicy, evaluate_provenance


def test_04_trusted_verifier_name_is_not_authenticated():
    policy = ProvenancePolicy("prov-v3", frozenset({"root"}), frozenset({"trusted-verifier"}))
    root = ProvenanceNode("root", frozenset(), "subject", "state", "ctx", "bundle", "trusted-verifier", "root-digest")
    forged = ProvenanceNode("e-node", frozenset({"root"}), "subject", "state", "ctx", "bundle", "trusted-verifier", "e-digest", "e1")
    result = evaluate_provenance(
        policy,
        (root, forged),
        subject_id="subject",
        subject_state_id="state",
        verification_context_id="ctx",
        policy_bundle_id="bundle",
        required_evidence_ids=frozenset({"e1"}),
        required_evidence_digests={"e1": "e-digest"},
    )
    assert result.decision is ProvenanceDecision.ALLOW
