from dataclasses import replace
from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.policy import policy_bundle_root, policy_object_root
from oma.provenance import ProvenanceDecision, evaluate_provenance
from oma.validation import ValidationDecision

_helpers = runpy.run_path(str(Path(__file__).with_name("test_execution.py")))
policy_enabled_input = _helpers["policy_enabled_input"]
initialized_store = _helpers["initialized_store"]


def _evidence_digest(item):
    return policy_object_root(
        "evidence-payload",
        {
            "evidence_id": item.evidence_id,
            "obligation_id": item.obligation_id,
            "subject_id": item.subject_id,
            "subject_state_id": item.subject_state_id,
            "verification_context_id": item.verification_context_id,
            "policy_bundle_id": item.policy_bundle_id,
            "passed": item.passed,
        },
    )


def test_caller_fabricated_provenance_trust_labels_cannot_terminalize(tmp_path):
    item = policy_enabled_input()
    forged_policy = replace(
        item.provenance_policy,
        trusted_root_ids=frozenset({"fabricated-root"}),
        trusted_verifier_ids=frozenset({"fabricated-verifier"}),
    )
    digest = _evidence_digest(item.evidence[0])
    forged_nodes = (
        replace(item.provenance_nodes[0], node_id="fabricated-root", verifier_id="fabricated-verifier"),
        replace(
            item.provenance_nodes[1],
            parent_ids=frozenset({"fabricated-root"}),
            verifier_id="fabricated-verifier",
            payload_digest=digest,
        ),
    )
    provenance = evaluate_provenance(
        forged_policy,
        forged_nodes,
        subject_id=item.acceptance_context.subject_id,
        subject_state_id=item.acceptance_context.subject_state_id,
        verification_context_id=item.acceptance_context.verification_context_id,
        policy_bundle_id=item.acceptance_context.policy_bundle_id,
        required_evidence_ids=frozenset({item.evidence[0].evidence_id}),
        required_evidence_digests={item.evidence[0].evidence_id: digest},
    )
    assert provenance.decision is ProvenanceDecision.ALLOW
    forged_root = provenance.provenance_root
    assert forged_root is not None

    bindings = tuple(
        replace(binding, policy_root=policy_object_root("provenance", forged_policy))
        if binding.policy_kind == "provenance"
        else binding
        for binding in item.expected_policy_bundle.bindings
    )
    bundle = replace(item.expected_policy_bundle, bindings=bindings)
    bundle_root = policy_bundle_root(bundle)
    forged = replace(
        item,
        provenance_policy=forged_policy,
        provenance_nodes=forged_nodes,
        expected_policy_bundle=bundle,
        snapshot=replace(item.snapshot, evidence_root=forged_root, policy_bundle_root=bundle_root),
        commit_state=replace(item.commit_state, evidence_root=forged_root, policy_bundle_root=bundle_root),
    )
    store = initialized_store(tmp_path / "oma.db", forged)
    result = execute_composed_pipeline(forged, store)
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0
