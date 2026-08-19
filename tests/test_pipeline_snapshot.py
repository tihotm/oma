from dataclasses import replace
from pathlib import Path
import runpy

from oma.pipeline import evaluate_composed_pipeline
from oma.validation import ValidationDecision

_policy_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline_policy.py")))
policy_enabled_input = _policy_tests["policy_enabled_input"]
by_node = runpy.run_path(str(Path(__file__).with_name("test_pipeline.py")))["by_node"]


def test_fresh_snapshot_reaches_terminal_allow_and_stops_at_atomic_commit():
    result = evaluate_composed_pipeline(policy_enabled_input())
    observations = by_node(result)
    assert observations["snapshot_freshness"].decision is ValidationDecision.ACCEPT
    assert observations["terminal_barrier"].decision is ValidationDecision.ACCEPT
    assert observations["commit_authorization"].decision is ValidationDecision.ACCEPT
    assert observations["atomic_commit"].decision is ValidationDecision.NOT_DONE
    assert result.result.decision is ValidationDecision.NOT_DONE


def test_forward_state_version_drift_is_stale_and_blocks_terminal_completion():
    item = policy_enabled_input()
    item = replace(item, commit_state=replace(item.commit_state, state_version=item.snapshot.state_version + 1))
    result = evaluate_composed_pipeline(item)
    observations = by_node(result)
    assert observations["snapshot_freshness"].decision is ValidationDecision.STALE
    assert observations["terminal_barrier"].decision is ValidationDecision.STALE
    assert result.result.decision is ValidationDecision.STALE


def test_state_version_rollback_is_integrity_block():
    item = policy_enabled_input()
    snapshot = replace(item.snapshot, state_version=2)
    current = replace(item.commit_state, state_version=1)
    result = evaluate_composed_pipeline(replace(item, snapshot=snapshot, commit_state=current))
    observations = by_node(result)
    assert observations["snapshot_freshness"].decision is ValidationDecision.BLOCK
    assert observations["terminal_barrier"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_terminal_epoch_rollback_is_integrity_block():
    item = policy_enabled_input()
    snapshot = replace(item.snapshot, terminal_epoch=2)
    current = replace(item.commit_state, terminal_epoch=1)
    token = replace(item.commit_token, terminal_epoch=2)
    result = evaluate_composed_pipeline(replace(item, snapshot=snapshot, commit_state=current, commit_token=token))
    assert by_node(result)["snapshot_freshness"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK


def test_evidence_root_forward_binding_drift_is_stale():
    item = policy_enabled_input()
    current = replace(item.commit_state, evidence_root="new-evidence-root")
    result = evaluate_composed_pipeline(replace(item, commit_state=current))
    assert by_node(result)["snapshot_freshness"].decision is ValidationDecision.STALE
    assert result.result.decision is ValidationDecision.STALE


def test_policy_bundle_root_drift_is_caught_before_terminal_commit():
    item = policy_enabled_input()
    current = replace(item.commit_state, policy_bundle_root="new-policy-root")
    result = evaluate_composed_pipeline(replace(item, commit_state=current))
    assert by_node(result)["policy_bundle"].decision is ValidationDecision.BLOCK
    assert by_node(result)["snapshot_freshness"].decision is ValidationDecision.STALE
    assert result.result.decision is ValidationDecision.BLOCK
