from oma.provenance import ProvenanceDecision, ProvenanceNode, ProvenancePolicy, evaluate_provenance


def test_unrelated_rooted_node_is_blocked():
    p=ProvenancePolicy("p",frozenset({"r"}),frozenset({"v"}))
    nodes=(
        ProvenanceNode("r",frozenset(),"s","st","vc","pb","v","rd"),
        ProvenanceNode("l",frozenset({"r"}),"s","st","vc","pb","v","ed","e"),
        ProvenanceNode("x",frozenset({"r"}),"s","st","vc","pb","v","xd"),
    )
    result=evaluate_provenance(p,nodes,subject_id="s",subject_state_id="st",verification_context_id="vc",policy_bundle_id="pb",required_evidence_ids=frozenset({"e"}))
    assert result.decision is ProvenanceDecision.BLOCK
