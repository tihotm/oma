from oma.retry import (
    RetryDecision,
    RetryDomain,
    RetryEvent,
    RetryEventKind,
    RetryPolicy,
    evaluate_retry_domain,
)


def policy(**overrides):
    values = dict(
        retry_policy_id="retry:v1",
        max_execution_attempts=3,
        max_cumulative_cost=100,
        authorized_retry_reasons=frozenset({"transient", "verifier_request"}),
        authorized_recovery_reasons=frozenset({"crash_resume"}),
    )
    values.update(overrides)
    return RetryPolicy(**values)


def domain(**overrides):
    values = dict(
        retry_domain_id="rd:1",
        subject_id="subject:1",
        pair_id="pair:1",
        lineage_id="lineage:1",
        retry_policy_id="retry:v1",
    )
    values.update(overrides)
    return RetryDomain(**values)


def event(sequence, kind, attempt_number, **overrides):
    values = dict(
        event_id=f"event:{sequence}",
        sequence=sequence,
        kind=kind,
        attempt_number=attempt_number,
        run_id="run:1",
        subject_id="subject:1",
        pair_id="pair:1",
        lineage_id="lineage:1",
        retry_domain_id="rd:1",
        retry_policy_id="retry:v1",
        reason="initial" if kind is RetryEventKind.INITIAL else (
            "transient" if kind is RetryEventKind.RETRY else "crash_resume"
        ),
        cost_units=10,
    )
    values.update(overrides)
    return RetryEvent(**values)


def test_empty_history_allowed():
    assert evaluate_retry_domain(policy(), domain(), []).decision is RetryDecision.ALLOW


def test_initial_allowed():
    result = evaluate_retry_domain(policy(), domain(), [event(1, RetryEventKind.INITIAL, 1)])
    assert result.decision is RetryDecision.ALLOW
    assert result.execution_attempts == 1
    assert result.cumulative_cost == 10


def test_retry_same_run_allowed():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RETRY, 2),
    ])
    assert result.decision is RetryDecision.ALLOW
    assert result.execution_attempts == 2


def test_new_run_does_not_reset_attempt_count():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1, run_id="run:1"),
        event(2, RetryEventKind.RETRY, 2, run_id="run:2"),
        event(3, RetryEventKind.RETRY, 3, run_id="run:3"),
    ])
    assert result.decision is RetryDecision.ALLOW
    assert result.execution_attempts == 3


def test_new_run_attempt_reset_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RETRY, 2, run_id="run:2"),
        event(3, RetryEventKind.RETRY, 2, run_id="run:3"),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_attempt_gap_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RETRY, 3),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_attempt_limit_blocks():
    result = evaluate_retry_domain(policy(max_execution_attempts=2), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RETRY, 2),
        event(3, RetryEventKind.RETRY, 3),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_budget_accumulates_across_runs():
    result = evaluate_retry_domain(policy(max_cumulative_cost=25), domain(), [
        event(1, RetryEventKind.INITIAL, 1, cost_units=10, run_id="run:1"),
        event(2, RetryEventKind.RETRY, 2, cost_units=10, run_id="run:2"),
        event(3, RetryEventKind.RECOVERY, 2, cost_units=10, run_id="run:3"),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_recovery_does_not_increment_execution_attempt():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RECOVERY, 1),
    ])
    assert result.decision is RetryDecision.ALLOW
    assert result.execution_attempts == 1


def test_recovery_unknown_attempt_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RECOVERY, 2),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_unauthorized_retry_reason_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RETRY, 2, reason="want_more_samples"),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_unauthorized_recovery_reason_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RECOVERY, 1, reason="reset_budget"),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_lineage_reset_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RETRY, 2, lineage_id="lineage:new"),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_subject_reset_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RETRY, 2, subject_id="subject:2"),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_pair_reset_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RETRY, 2, pair_id="pair:2"),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_retry_domain_reset_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RETRY, 2, retry_domain_id="rd:new"),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_retry_policy_binding_change_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.RETRY, 2, retry_policy_id="retry:v2"),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_duplicate_event_id_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1, event_id="same"),
        event(2, RetryEventKind.RETRY, 2, event_id="same"),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_event_sequence_gap_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(3, RetryEventKind.RETRY, 2),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_retry_without_initial_blocks():
    assert evaluate_retry_domain(policy(), domain(), [event(1, RetryEventKind.RETRY, 1)]).decision is RetryDecision.BLOCK


def test_recovery_without_initial_blocks():
    assert evaluate_retry_domain(policy(), domain(), [event(1, RetryEventKind.RECOVERY, 1)]).decision is RetryDecision.BLOCK


def test_second_initial_blocks():
    result = evaluate_retry_domain(policy(), domain(), [
        event(1, RetryEventKind.INITIAL, 1),
        event(2, RetryEventKind.INITIAL, 1),
    ])
    assert result.decision is RetryDecision.BLOCK


def test_negative_cost_blocks():
    assert evaluate_retry_domain(policy(), domain(), [event(1, RetryEventKind.INITIAL, 1, cost_units=-1)]).decision is RetryDecision.BLOCK


def test_policy_domain_mismatch_blocks():
    assert evaluate_retry_domain(policy(retry_policy_id="retry:v2"), domain(), []).decision is RetryDecision.BLOCK
