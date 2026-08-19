from dataclasses import replace

from oma.terminal import (
    TerminalDecision,
    TerminalPolicy,
    canonical_terminal_policy,
    evaluate_terminal_barrier,
)
from oma.validation import ValidationDecision, ValidationObservation


def obs(node_id, decision=ValidationDecision.ACCEPT, root=None):
    return ValidationObservation(node_id, decision, root or f"root:{node_id}")


def policy():
    return canonical_terminal_policy("termination:v1")


def complete(decision=ValidationDecision.ACCEPT):
    return tuple(obs(node_id, decision) for node_id in sorted(policy().required_node_ids))


def test_complete_accepting_prerequisites_allow_commit():
    result = evaluate_terminal_barrier(policy(), complete(), requested_action="COMMIT")
    assert result.decision is TerminalDecision.ALLOW
    assert result.terminal_barrier_root


def test_complete_accepting_prerequisites_allow_done():
    assert evaluate_terminal_barrier(policy(), complete(), requested_action="DONE").decision is TerminalDecision.ALLOW


def test_root_is_deterministic():
    first = evaluate_terminal_barrier(policy(), complete(), requested_action="COMMIT")
    second = evaluate_terminal_barrier(policy(), tuple(reversed(complete())), requested_action="COMMIT")
    assert first.terminal_barrier_root == second.terminal_barrier_root


def test_missing_prerequisite_is_not_done():
    items = tuple(item for item in complete() if item.node_id != "aggregation")
    result = evaluate_terminal_barrier(policy(), items, requested_action="COMMIT")
    assert result.decision is TerminalDecision.NOT_DONE


def test_not_done_prerequisite_cannot_be_masked_by_commit():
    items = tuple(obs(item.node_id, ValidationDecision.NOT_DONE if item.node_id == "aggregation" else ValidationDecision.ACCEPT) for item in complete())
    result = evaluate_terminal_barrier(policy(), items, requested_action="COMMIT")
    assert result.decision is TerminalDecision.NOT_DONE


def test_stale_precedes_not_done():
    items = tuple(obs(item.node_id, ValidationDecision.STALE if item.node_id == "trust_temporal" else (ValidationDecision.NOT_DONE if item.node_id == "aggregation" else ValidationDecision.ACCEPT)) for item in complete())
    assert evaluate_terminal_barrier(policy(), items, requested_action="COMMIT").decision is TerminalDecision.STALE


def test_block_precedes_stale_and_not_done():
    items = tuple(obs(item.node_id, ValidationDecision.BLOCK if item.node_id == "policy_bundle" else (ValidationDecision.STALE if item.node_id == "trust_temporal" else (ValidationDecision.NOT_DONE if item.node_id == "aggregation" else ValidationDecision.ACCEPT))) for item in complete())
    assert evaluate_terminal_barrier(policy(), items, requested_action="COMMIT").decision is TerminalDecision.BLOCK


def test_unexpected_prerequisite_blocks():
    result = evaluate_terminal_barrier(policy(), complete() + (obs("commit_authorization"),), requested_action="COMMIT")
    assert result.decision is TerminalDecision.BLOCK


def test_duplicate_prerequisite_blocks():
    result = evaluate_terminal_barrier(policy(), complete() + (obs("aggregation"),), requested_action="COMMIT")
    assert result.decision is TerminalDecision.BLOCK


def test_missing_evidence_root_blocks():
    items = list(complete())
    items[0] = ValidationObservation(items[0].node_id, items[0].decision, "")
    assert evaluate_terminal_barrier(policy(), items, requested_action="COMMIT").decision is TerminalDecision.BLOCK


def test_unknown_action_blocks():
    assert evaluate_terminal_barrier(policy(), complete(), requested_action="FORCE_COMMIT").decision is TerminalDecision.BLOCK


def test_empty_policy_id_blocks():
    assert evaluate_terminal_barrier(replace(policy(), termination_policy_id=""), complete(), requested_action="COMMIT").decision is TerminalDecision.BLOCK


def test_empty_required_set_blocks():
    assert evaluate_terminal_barrier(replace(policy(), required_node_ids=frozenset()), (), requested_action="COMMIT").decision is TerminalDecision.BLOCK


def test_empty_allowed_actions_blocks():
    assert evaluate_terminal_barrier(replace(policy(), allowed_actions=frozenset()), complete(), requested_action="COMMIT").decision is TerminalDecision.BLOCK


def test_policy_cannot_drop_aggregation_and_still_use_canonical_closure():
    weakened = replace(policy(), required_node_ids=policy().required_node_ids - {"aggregation"})
    result = evaluate_terminal_barrier(weakened, tuple(item for item in complete() if item.node_id != "aggregation"), requested_action="COMMIT")
    assert result.decision is TerminalDecision.ALLOW
    assert weakened != policy()


def test_action_changes_barrier_root():
    commit = evaluate_terminal_barrier(policy(), complete(), requested_action="COMMIT")
    done = evaluate_terminal_barrier(policy(), complete(), requested_action="DONE")
    assert commit.terminal_barrier_root != done.terminal_barrier_root
