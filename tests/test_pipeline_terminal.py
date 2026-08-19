from dataclasses import replace
from pathlib import Path
import runpy

from oma.pipeline import evaluate_composed_pipeline
from oma.validation import ValidationDecision

_policy_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline_policy.py")))
policy_enabled_input = _policy_tests["policy_enabled_input"]
by_node = runpy.run_path(str(Path(__file__).with_name("test_pipeline.py")))["by_node"]


def test_terminal_barrier_allows_when_all_prerequisites_are_fresh():
    result = evaluate_composed_pipeline(policy_enabled_input())
    observations = by_node(result)
    assert observations["policy_bundle"].decision is ValidationDecision.ACCEPT
    assert observations["aggregation"].decision is ValidationDecision.ACCEPT
    assert observations["snapshot_freshness"].decision is ValidationDecision.ACCEPT
    assert observations["terminal_barrier"].decision is ValidationDecision.ACCEPT
    assert observations["commit_authorization"].decision is ValidationDecision.ACCEPT
    assert observations["atomic_commit"].decision is ValidationDecision.NOT_DONE
    assert result.result.decision is ValidationDecision.NOT_DONE


def test_force_commit_action_is_blocked():
    item = replace(policy_enabled_input(), terminal_action="FORCE_COMMIT")
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["terminal_barrier"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_stale_prerequisite_cannot_be_masked_by_terminal_request():
    item = policy_enabled_input()
    item = replace(item, authority_context=replace(item.authority_context, authority_epoch=2))
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["terminal_barrier"].decision in {ValidationDecision.STALE, ValidationDecision.BLOCK}
    assert result.result.decision in {ValidationDecision.STALE, ValidationDecision.BLOCK}


def test_blocked_prerequisite_cannot_be_masked_by_terminal_request():
    item = policy_enabled_input()
    item = replace(item, evidence=(replace(item.evidence[0], subject_id="other"),))
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["terminal_barrier"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_missing_termination_policy_is_not_done_not_accept():
    item = replace(policy_enabled_input(), termination_policy_id=None, expected_policy_bundle=None)
    result = evaluate_composed_pipeline(item)
    assert by_node(result)["terminal_barrier"].decision is ValidationDecision.NOT_DONE
    assert result.result.decision is ValidationDecision.NOT_DONE
