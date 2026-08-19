from oma.provenance import ProvenanceDecision, ProvenanceNode, ProvenancePolicy, evaluate_provenance


def test_newline_evidence_id_is_accepted():
    policy=ProvenancePolicy("p",frozenset({"r"}),frozenset({"v"}))
    nodes=(
        ProvenanceNode("r",frozenset(),"s","st","vc","pb","v","rd"),
        ProvenanceNode("l",frozenset({"r"}),"s","st","vc","pb","v","ed","e\n1"),
    )
    result=evaluate_provenance(policy,nodes,subject_id="s",subject_state_id="st",verification_context_id="vc",policy_bundle_id="pb",required_evidence_ids=frozenset({"e\n1"}))
    assert result.decision is ProvenanceDecision.ALLOW
