from oma.provenance import ProvenanceDecision, ProvenanceNode, ProvenancePolicy, evaluate_provenance


def test_newline_verifier_id_is_accepted_when_policy_trusts_same_string():
    policy=ProvenancePolicy("p",frozenset({"r"}),frozenset({"v\n1"}))
    nodes=(
        ProvenanceNode("r",frozenset(),"s","st","vc","pb","v\n1","rd"),
        ProvenanceNode("l",frozenset({"r"}),"s","st","vc","pb","v\n1","ed","e"),
    )
    result=evaluate_provenance(policy,nodes,subject_id="s",subject_state_id="st",verification_context_id="vc",policy_bundle_id="pb",required_evidence_ids=frozenset({"e"}))
    assert result.decision is ProvenanceDecision.ALLOW
