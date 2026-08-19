from dataclasses import replace

from oma.provenance import (
    ProvenanceDecision,
    ProvenanceNode,
    ProvenancePolicy,
    evaluate_provenance,
)


def base():
    policy = ProvenancePolicy(
        "prov:v1",
        frozenset({"root"}),
        frozenset({"verifier"}),
    )
    root = ProvenanceNode("root", frozenset(), "s", "st", "v", "p", "verifier", "d0")
    leaf = ProvenanceNode("leaf", frozenset({"root"}), "s", "st", "v", "p", "verifier", "d1", "e1")
    return policy, (root, leaf)


def evaluate(policy, nodes, required=frozenset({"e1"})):
    return evaluate_provenance(
        policy,
        nodes,
        subject_id="s",
        subject_state_id="st",
        verification_context_id="v",
        policy_bundle_id="p",
        required_evidence_ids=required,
    )


def test_valid_provenance_allows():
    assert evaluate(*base()).decision is ProvenanceDecision.ALLOW


def test_provenance_root_is_deterministic():
    assert evaluate(*base()).provenance_root == evaluate(*base()).provenance_root


def test_duplicate_node_blocks():
    policy, nodes = base()
    assert evaluate(policy, nodes + (nodes[1],)).decision is ProvenanceDecision.BLOCK


def test_missing_parent_blocks():
    policy, nodes = base()
    bad = replace(nodes[1], parent_ids=frozenset({"missing"}))
    assert evaluate(policy, (nodes[0], bad)).decision is ProvenanceDecision.BLOCK


def test_cycle_blocks():
    policy, nodes = base()
    a = replace(nodes[0], node_id="a", parent_ids=frozenset({"b"}))
    b = replace(nodes[1], node_id="b", parent_ids=frozenset({"a"}))
    policy = replace(policy, trusted_root_ids=frozenset({"a"}))
    assert evaluate(policy, (a, b)).decision is ProvenanceDecision.BLOCK


def test_revoked_leaf_blocks():
    policy, nodes = base()
    policy = replace(policy, revoked_node_ids=frozenset({"leaf"}))
    assert evaluate(policy, nodes).decision is ProvenanceDecision.BLOCK


def test_revoked_root_blocks():
    policy, nodes = base()
    policy = replace(policy, revoked_node_ids=frozenset({"root"}))
    assert evaluate(policy, nodes).decision is ProvenanceDecision.BLOCK


def test_subject_mismatch_blocks():
    policy, nodes = base()
    assert evaluate(policy, (nodes[0], replace(nodes[1], subject_id="x"))).decision is ProvenanceDecision.BLOCK


def test_state_mismatch_blocks():
    policy, nodes = base()
    assert evaluate(policy, (nodes[0], replace(nodes[1], subject_state_id="x"))).decision is ProvenanceDecision.BLOCK


def test_verification_context_mismatch_blocks():
    policy, nodes = base()
    bad = replace(nodes[1], verification_context_id="x")
    assert evaluate(policy, (nodes[0], bad)).decision is ProvenanceDecision.BLOCK


def test_policy_binding_mismatch_blocks():
    policy, nodes = base()
    assert evaluate(policy, (nodes[0], replace(nodes[1], policy_bundle_id="x"))).decision is ProvenanceDecision.BLOCK


def test_untrusted_verifier_blocks():
    policy, nodes = base()
    assert evaluate(policy, (nodes[0], replace(nodes[1], verifier_id="evil"))).decision is ProvenanceDecision.BLOCK


def test_missing_evidence_provenance_blocks():
    policy, nodes = base()
    assert evaluate(policy, (nodes[0],)).decision is ProvenanceDecision.BLOCK


def test_unexpected_evidence_provenance_blocks():
    policy, nodes = base()
    extra = replace(nodes[1], node_id="leaf2", evidence_id="e2")
    assert evaluate(policy, nodes + (extra,)).decision is ProvenanceDecision.BLOCK


def test_duplicate_evidence_provenance_blocks():
    policy, nodes = base()
    extra = replace(nodes[1], node_id="leaf2")
    assert evaluate(policy, nodes + (extra,)).decision is ProvenanceDecision.BLOCK


def test_unrelated_branch_blocks():
    policy, nodes = base()
    unrelated = replace(nodes[1], node_id="unrelated", evidence_id=None)
    assert evaluate(policy, nodes + (unrelated,)).decision is ProvenanceDecision.BLOCK


def test_trusted_root_with_parent_blocks():
    policy, nodes = base()
    bad_root = replace(nodes[0], parent_ids=frozenset({"leaf"}))
    assert evaluate(policy, (bad_root, nodes[1])).decision is ProvenanceDecision.BLOCK


def test_nonroot_without_parent_blocks():
    policy, nodes = base()
    bad_leaf = replace(nodes[1], parent_ids=frozenset())
    assert evaluate(policy, (nodes[0], bad_leaf)).decision is ProvenanceDecision.BLOCK


def test_missing_trusted_root_blocks():
    policy, nodes = base()
    assert evaluate(policy, (nodes[1],)).decision is ProvenanceDecision.BLOCK


def test_unknown_revoked_node_blocks():
    policy, nodes = base()
    policy = replace(policy, revoked_node_ids=frozenset({"ghost"}))
    assert evaluate(policy, nodes).decision is ProvenanceDecision.BLOCK


def test_payload_digest_binding_allows():
    policy, nodes = base()
    result = evaluate_provenance(
        policy,
        nodes,
        subject_id="s",
        subject_state_id="st",
        verification_context_id="v",
        policy_bundle_id="p",
        required_evidence_ids=frozenset({"e1"}),
        required_evidence_digests={"e1": "d1"},
    )
    assert result.decision is ProvenanceDecision.ALLOW


def test_payload_digest_mismatch_blocks():
    policy, nodes = base()
    result = evaluate_provenance(
        policy,
        nodes,
        subject_id="s",
        subject_state_id="st",
        verification_context_id="v",
        policy_bundle_id="p",
        required_evidence_ids=frozenset({"e1"}),
        required_evidence_digests={"e1": "other"},
    )
    assert result.decision is ProvenanceDecision.BLOCK
