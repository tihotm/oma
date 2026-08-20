import pytest

from oma.policy import policy_object_root
from oma.provenance import ProvenanceDecision, ProvenanceNode, ProvenancePolicy, evaluate_provenance


def test_v13_15_root_equivalent_provenance_container_type_can_crash_gate():
    left = ProvenancePolicy("prov:v1", frozenset({"root"}), frozenset({"verifier"}))
    right = ProvenancePolicy("prov:v1", ["root"], ["verifier"])
    node = ProvenanceNode("root", frozenset(), "subject:1", "state:1", "verify:1", "bundle:1", "verifier", "digest:1", "ev:1")
    assert policy_object_root("provenance", left) == policy_object_root("provenance", right)
    assert evaluate_provenance(
        left,
        (node,),
        subject_id="subject:1",
        subject_state_id="state:1",
        verification_context_id="verify:1",
        policy_bundle_id="bundle:1",
        required_evidence_ids=frozenset({"ev:1"}),
        required_evidence_digests={"ev:1": "digest:1"},
    ).decision is ProvenanceDecision.ALLOW
    with pytest.raises(TypeError):
        evaluate_provenance(
            right,
            (node,),
            subject_id="subject:1",
            subject_state_id="state:1",
            verification_context_id="verify:1",
            policy_bundle_id="bundle:1",
            required_evidence_ids=frozenset({"ev:1"}),
            required_evidence_digests={"ev:1": "digest:1"},
        )
