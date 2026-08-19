from dataclasses import replace

from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.retry_ledger import RetryLedgerDecision, SQLiteRetryLedger


def policy(**overrides):
    values = dict(
        retry_policy_id="retry:v1",
        max_execution_attempts=2,
        max_cumulative_cost=10,
        authorized_retry_reasons=frozenset({"verification_failed"}),
        authorized_recovery_reasons=frozenset({"process_restart"}),
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


def event(sequence, kind, attempt, **overrides):
    values = dict(
        event_id=f"event:{sequence}",
        sequence=sequence,
        kind=kind,
        attempt_number=attempt,
        run_id=f"run:{sequence}",
        subject_id="subject:1",
        pair_id="pair:1",
        lineage_id="lineage:1",
        retry_domain_id="rd:1",
        retry_policy_id="retry:v1",
        reason="initial" if kind is RetryEventKind.INITIAL else "verification_failed",
        cost_units=1,
    )
    values.update(overrides)
    return RetryEvent(**values)


def test_initial_history_persists_across_reopen(tmp_path):
    path = tmp_path / "oma.db"
    ledger = SQLiteRetryLedger(path)
    first = event(1, RetryEventKind.INITIAL, 1)
    assert ledger.initialize(policy(), domain(), first).decision is RetryLedgerDecision.WRITTEN
    reopened = SQLiteRetryLedger(path)
    assert reopened.get(policy(), domain()) == (first,)


def test_duplicate_domain_initialization_conflicts(tmp_path):
    ledger = SQLiteRetryLedger(tmp_path / "oma.db")
    first = event(1, RetryEventKind.INITIAL, 1)
    assert ledger.initialize(policy(), domain(), first).decision is RetryLedgerDecision.WRITTEN
    assert ledger.initialize(policy(), domain(), first).decision is RetryLedgerDecision.CONFLICT


def test_append_is_sequence_monotonic(tmp_path):
    ledger = SQLiteRetryLedger(tmp_path / "oma.db")
    first = event(1, RetryEventKind.INITIAL, 1)
    ledger.initialize(policy(), domain(), first)
    gap = event(3, RetryEventKind.RETRY, 2)
    assert ledger.append(policy(), domain(), gap).decision is RetryLedgerDecision.BLOCK
    assert ledger.get(policy(), domain()) == (first,)


def test_over_limit_event_is_preserved_as_factual_block(tmp_path):
    ledger = SQLiteRetryLedger(tmp_path / "oma.db")
    first = event(1, RetryEventKind.INITIAL, 1)
    second = event(2, RetryEventKind.RETRY, 2)
    third = event(3, RetryEventKind.RETRY, 3)
    ledger.initialize(policy(), domain(), first)
    assert ledger.append(policy(), domain(), second).decision is RetryLedgerDecision.WRITTEN
    blocked = ledger.append(policy(), domain(), third)
    assert blocked.decision is RetryLedgerDecision.BLOCKED
    assert blocked.retry_result is not None
    assert ledger.get(policy(), domain()) == (first, second, third)


def test_policy_content_change_cannot_read_same_domain(tmp_path):
    ledger = SQLiteRetryLedger(tmp_path / "oma.db")
    ledger.initialize(policy(), domain(), event(1, RetryEventKind.INITIAL, 1))
    assert ledger.get(policy(max_execution_attempts=3), domain()) is None


def test_domain_binding_change_cannot_read_same_domain(tmp_path):
    ledger = SQLiteRetryLedger(tmp_path / "oma.db")
    ledger.initialize(policy(), domain(), event(1, RetryEventKind.INITIAL, 1))
    assert ledger.get(policy(), domain(pair_id="other")) is None


def test_duplicate_event_id_conflicts_without_rewrite(tmp_path):
    ledger = SQLiteRetryLedger(tmp_path / "oma.db")
    first = event(1, RetryEventKind.INITIAL, 1)
    second = event(2, RetryEventKind.RETRY, 2, event_id="event:2")
    ledger.initialize(policy(), domain(), first)
    ledger.append(policy(), domain(), second)
    duplicate = event(3, RetryEventKind.RETRY, 3, event_id="event:2")
    assert ledger.append(policy(), domain(), duplicate).decision is RetryLedgerDecision.CONFLICT
    assert ledger.get(policy(), domain()) == (first, second)


def test_binding_mismatch_is_not_persisted(tmp_path):
    ledger = SQLiteRetryLedger(tmp_path / "oma.db")
    first = event(1, RetryEventKind.INITIAL, 1)
    ledger.initialize(policy(), domain(), first)
    bad = event(2, RetryEventKind.RETRY, 2, subject_id="other")
    assert ledger.append(policy(), domain(), bad).decision is RetryLedgerDecision.BLOCK
    assert ledger.get(policy(), domain()) == (first,)
