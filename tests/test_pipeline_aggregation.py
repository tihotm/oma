from dataclasses import replace
from pathlib import Path
import runpy

from oma.aggregation import AggregationPolicy
from oma.pipeline import evaluate_composed_pipeline
from oma.validation import ValidationDecision


_pipeline_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline.py")))
valid_input = _pipeline_tests["valid_input"]
by_node = _pipeline_tests["by_node"]


def valid_aggregation_policy(item):
    return AggregationPolicy(
        aggregation_policy_id="aggregation:v1",
        expected_evidence_set_id="evidence-set:v1",
        expected_evidence_ids=frozenset(e.evidence_id for e in item.evidence),
        subject_id=item.acceptance_context.subject_id,
        subject_state_id=item.acceptance_context.subject_state_id,
        verification_context_id=item.acceptance_context.verification_context_id,
        policy_bundle_id=item.acceptance_context.policy_bundle_id,
        pair_id=item.retry_domain.pair_id,
        run_id=item.retry_events[-1].run_id,
    )


def test_valid_aggregation_policy_is_bound_into_pipeline():
    item = valid_input()
    item = replace(item, aggregation_policy=valid_aggregation_policy(item))
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["aggregation"].decision is ValidationDecision.ACCEPT
    assert result.result.decision is ValidationDecision.NOT_DONE


def test_missing_aggregation_policy_remains_not_done():
    result = evaluate_composed_pipeline(valid_input())
    assert by_node(result)["aggregation"].decision is ValidationDecision.NOT_DONE


def test_expected_set_substitution_blocks_pipeline():
    item = valid_input()
    policy = replace(
        valid_aggregation_policy(item),
        expected_evidence_ids=frozenset({"other-evidence"}),
    )
    result = evaluate_composed_pipeline(replace(item, aggregation_policy=policy))
    assert by_node(result)["aggregation"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_cross_run_reuse_blocks_pipeline():
    item = valid_input()
    policy = replace(valid_aggregation_policy(item), run_id="other-run")
    result = evaluate_composed_pipeline(replace(item, aggregation_policy=policy))
    assert by_node(result)["aggregation"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_cross_pair_reuse_blocks_pipeline():
    item = valid_input()
    policy = replace(valid_aggregation_policy(item), pair_id="other-pair")
    result = evaluate_composed_pipeline(replace(item, aggregation_policy=policy))
    assert by_node(result)["aggregation"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_invalid_aggregation_policy_blocks_pipeline():
    item = valid_input()
    policy = replace(valid_aggregation_policy(item), expected_evidence_set_id="")
    result = evaluate_composed_pipeline(replace(item, aggregation_policy=policy))
    assert by_node(result)["aggregation"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK
