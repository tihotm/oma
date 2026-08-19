from dataclasses import replace
from pathlib import Path
import runpy

from oma.obligation import obligation_root
from oma.pipeline import evaluate_composed_pipeline
from oma.policy import PolicyBinding, PolicyBundle, policy_bundle_root, policy_object_root
from oma.validation import ValidationDecision


_pipeline_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline.py")))
_aggregation_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline_aggregation.py")))
valid_input = _pipeline_tests["valid_input"]
by_node = _pipeline_tests["by_node"]
valid_aggregation_policy = _aggregation_tests["valid_aggregation_policy"]


def policy_enabled_input():
    item = valid_input()
    aggregation_policy = valid_aggregation_policy(item)
    termination_policy_id = "termination:v1"
    bindings = (
        PolicyBinding(
            "serialization",
            item.schema.schema_id,
            policy_object_root("serialization", item.schema),
        ),
        PolicyBinding(
            "identity",
            item.identity_policy.identity_policy_id,
            policy_object_root("identity", item.identity_policy),
        ),
        PolicyBinding(
            "scope",
            item.scope_policy.scope_policy_id,
            policy_object_root("scope", item.scope_policy),
        ),
        PolicyBinding(
            "authority",
            item.authority_context.authority_context_id,
            policy_object_root("authority", item.authority_context),
        ),
        PolicyBinding(
            "trust",
            item.trust_context.temporal_context_id,
            policy_object_root("trust", item.trust_roots),
        ),
        PolicyBinding(
            "obligation",
            item.presented_obligation_manifest.obligation_set_id,
            obligation_root(item.presented_obligation_manifest),
        ),
        PolicyBinding(
            "provenance",
            item.provenance_policy.provenance_policy_id,
            policy_object_root("provenance", item.provenance_policy),
        ),
        PolicyBinding(
            "aggregation",
            aggregation_policy.aggregation_policy_id,
            policy_object_root("aggregation", aggregation_policy),
        ),
        PolicyBinding(
            "retry",
            item.retry_policy.retry_policy_id,
            policy_object_root("retry", item.retry_policy),
        ),
        PolicyBinding(
            "termination",
            termination_policy_id,
            policy_object_root("termination", termination_policy_id),
        ),
    )
    bundle = PolicyBundle(
        policy_bundle_id=item.acceptance_context.policy_bundle_id,
        bundle_epoch=1,
        bindings=bindings,
    )
    root = policy_bundle_root(bundle)
    return replace(
        item,
        aggregation_policy=aggregation_policy,
        expected_policy_bundle=bundle,
        termination_policy_id=termination_policy_id,
        snapshot=replace(item.snapshot, policy_bundle_root=root),
        commit_state=replace(item.commit_state, policy_bundle_root=root),
    )


def test_valid_policy_bundle_is_bound_into_pipeline():
    item = policy_enabled_input()
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["policy_bundle"].decision is ValidationDecision.ACCEPT
    assert by_node(result)["aggregation"].decision is ValidationDecision.ACCEPT
    assert result.result.decision is ValidationDecision.NOT_DONE


def test_missing_policy_bundle_is_not_done():
    item = policy_enabled_input()
    item = replace(item, expected_policy_bundle=None)
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["policy_bundle"].decision is ValidationDecision.NOT_DONE


def test_scope_policy_mutation_after_bundle_blocks():
    item = policy_enabled_input()
    item = replace(
        item,
        scope_policy=replace(item.scope_policy, allowed_paths=("src", "docs")),
    )
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["policy_bundle"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_retry_policy_mutation_after_bundle_blocks():
    item = policy_enabled_input()
    item = replace(
        item,
        retry_policy=replace(item.retry_policy, max_execution_attempts=3),
    )
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["policy_bundle"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_schema_mutation_after_bundle_blocks():
    item = policy_enabled_input()
    item = replace(
        item,
        schema=replace(item.schema, optional_fields=frozenset({"optional"})),
    )
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["parse_schema"].decision is ValidationDecision.ACCEPT
    assert by_node(result)["policy_bundle"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_termination_policy_substitution_blocks():
    item = policy_enabled_input()
    result = evaluate_composed_pipeline(
        replace(item, termination_policy_id="termination:evil")
    )
    assert by_node(result)["policy_bundle"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_snapshot_policy_bundle_root_mismatch_blocks():
    item = policy_enabled_input()
    item = replace(item, snapshot=replace(item.snapshot, policy_bundle_root="wrong"))
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["policy_bundle"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_current_policy_bundle_root_mismatch_blocks():
    item = policy_enabled_input()
    item = replace(item, commit_state=replace(item.commit_state, policy_bundle_root="wrong"))
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["policy_bundle"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_bound_policy_bundle_id_mismatch_blocks():
    item = policy_enabled_input()
    item = replace(
        item,
        acceptance_context=replace(item.acceptance_context, policy_bundle_id="other"),
    )
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["policy_bundle"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_expected_bundle_epoch_change_without_snapshot_root_change_blocks():
    item = policy_enabled_input()
    changed = replace(item.expected_policy_bundle, bundle_epoch=2)
    result = evaluate_composed_pipeline(replace(item, expected_policy_bundle=changed))
    assert by_node(result)["policy_bundle"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK
