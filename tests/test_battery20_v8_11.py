from oma.provenance import ProvenanceDecision, ProvenanceNode, ProvenancePolicy, evaluate_provenance


def build(subject,state):
    policy=ProvenancePolicy("p",frozenset({"r"}),frozenset({"v"}))
    nodes=(
        ProvenanceNode("r",frozenset(),subject,state,"vc","pb","v","root-d"),
        ProvenanceNode("l",frozenset({"r"}),subject,state,"vc","pb","v","ev-d","e"),
    )
    return evaluate_provenance(policy,nodes,subject_id=subject,subject_state_id=state,verification_context_id="vc",policy_bundle_id="pb",required_evidence_ids=frozenset({"e"}))

def test_distinct_contexts_can_share_provenance_root_via_nul_shift():
    a=build("s","x\x00y"); b=build("s\x00x","y")
    assert a.decision is ProvenanceDecision.ALLOW and b.decision is ProvenanceDecision.ALLOW
    assert a.provenance_root == b.provenance_root
