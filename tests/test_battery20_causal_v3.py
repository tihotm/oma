from dataclasses import replace

from oma.provenance import (
    ProvenanceDecision,
    ProvenanceNode,
    ProvenancePolicy,
    evaluate_provenance,
)


def _prov_policy():
    return ProvenancePolicy(
        provenance_policy_id="prov-v3",
        trusted_root_ids=frozenset({"root"}),
        trusted_verifier_ids=frozenset({"verifier"}),
    )


def _prov_nodes():
    root = ProvenanceNode(
        node_id="root",
        parent_ids=frozenset(),
        subject_id="subject",
        subject_state_id="state",
        verification_context_id="ctx",
        policy_bundle_id="bundle",
        verifier_id="verifier",
        payload_digest="root-digest",
    )
    evidence = ProvenanceNode(
        node_id="node-e1",
        parent_ids=frozenset({"root"}),
        subject_id="subject",
        subject_state_id="state",
        verification_context_id="ctx",
        policy_bundle_id="bundle",
        verifier_id="verifier",
        payload_digest="digest-e1",
        evidence_id="e1",
    )
    return root, evidence


def _eval(nodes, *, digests=None):
    return evaluate_provenance(
        _prov_policy(),
        nodes,
        subject_id="subject",
        subject_state_id="state",
        verification_context_id="ctx",
        policy_bundle_id="bundle",
        required_evidence_ids=frozenset({"e1"}),
        required_evidence_digests=digests,
    )


def test_01_duplicate_provenance_node_blocks():
    root, evidence = _prov_nodes()
    duplicate = replace(evidence, payload_digest="different")
    result = _eval((root, evidence, duplicate))
    assert result.decision is ProvenanceDecision.BLOCK
    assert "invalid_or_duplicate_provenance_node" in result.reasons


def test_02_provenance_payload_substitution_blocks():
    root, evidence = _prov_nodes()
    result = _eval((root, evidence), digests={"e1": "expected-digest"})
    assert result.decision is ProvenanceDecision.BLOCK
    assert "evidence_payload_digest_mismatch:e1" in result.reasons


def test_03_unrelated_provenance_branch_blocks():
    root, evidence = _prov_nodes()
    unrelated = replace(
        evidence,
        node_id="unrelated",
        evidence_id=None,
        payload_digest="unrelated-digest",
    )
    result = _eval((root, evidence, unrelated))
    assert result.decision is ProvenanceDecision.BLOCK
    assert "provenance_contains_unrelated_nodes" in result.reasons
