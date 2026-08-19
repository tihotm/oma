from oma.provenance import ProvenanceDecision, ProvenanceNode, ProvenancePolicy, evaluate_provenance


def test_05_trusted_provenance_root_name_is_not_authenticated():
    policy = ProvenancePolicy("prov-v3", frozenset({"trusted-root"}), frozenset({"verifier"}))
    forged_root = ProvenanceNode("trusted-root", frozenset(), "subject", "state", "ctx", "bundle", "verifier", "attacker-root")
    evidence = ProvenanceNode("e-node", frozenset({"trusted-root"}), "subject", "state", "ctx", "bundle", "verifier", "e-digest", "e1")
    result = evaluate_provenance(
        policy,
        (forged_root, evidence),
        subject_id="subject",
        subject_state_id="state",
        verification_context_id="ctx",
        policy_bundle_id="bundle",
        required_evidence_ids=frozenset({"e1"}),
        required_evidence_digests={"e1": "e-digest"},
    )
    assert result.decision is ProvenanceDecision.ALLOW
