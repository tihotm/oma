from oma.provenance import ProvenanceDecision, ProvenanceNode, ProvenancePolicy, evaluate_provenance


def test_non_root_cycle_is_blocked():
    p=ProvenancePolicy("p",frozenset({"r"}),frozenset({"v"}))
    nodes=(
        ProvenanceNode("r",frozenset(),"s","st","vc","pb","v","rd"),
        ProvenanceNode("a",frozenset({"b","r"}),"s","st","vc","pb","v","ad","e"),
        ProvenanceNode("b",frozenset({"a"}),"s","st","vc","pb","v","bd"),
    )
    result=evaluate_provenance(p,nodes,subject_id="s",subject_state_id="st",verification_context_id="vc",policy_bundle_id="pb",required_evidence_ids=frozenset({"e"}))
    assert result.decision is ProvenanceDecision.BLOCK
