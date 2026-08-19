from dataclasses import replace
from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.retry_ledger import RetryLedgerDecision, SQLiteRetryLedger
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision
from oma.validation import ValidationDecision


_policy_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline_policy.py")))
policy_enabled_input = _policy_tests["policy_enabled_input"]
by_node = runpy.run_path(str(Path(__file__).with_name("test_pipeline.py")))["by_node"]


def initialized_store(path, item):
    store = SQLiteTerminalStore(path)
    result = store.initialize_subject_state(item.commit_state)
    assert result.decision is SubjectStateDecision.WRITTEN
    retry = SQLiteRetryLedger(path)
    assert retry.initialize(
        item.retry_policy,
        item.retry_domain,
        item.retry_events[0],
    ).decision is RetryLedgerDecision.WRITTEN
    return store


def test_fully_valid_pipeline_commits_durably_and_accepts(tmp_path):
    item = policy_enabled_input()
    store = initialized_store(tmp_path / "oma.db", item)
    result = execute_composed_pipeline(item, store)
    observations = by_node(result)
    assert observations["snapshot_freshness"].decision is ValidationDecision.ACCEPT
    assert observations["terminal_barrier"].decision is ValidationDecision.ACCEPT
    assert observations["commit_authorization"].decision is ValidationDecision.ACCEPT
    assert observations["atomic_commit"].decision is ValidationDecision.ACCEPT
    assert result.result.decision is ValidationDecision.ACCEPT
    assert store.count() == 1


def test_committed_record_survives_store_reopen(tmp_path):
    item = policy_enabled_input()
    path = tmp_path / "oma.db"
    store = initialized_store(path, item)
    result = execute_composed_pipeline(item, store)
    assert result.result.decision is ValidationDecision.ACCEPT
    reopened = SQLiteTerminalStore(path)
    record = reopened.get(item.terminal_commit_id)
    assert record is not None
    assert record.acceptance_snapshot_id == item.snapshot.acceptance_snapshot_id
    assert record.policy_bundle_root == item.snapshot.policy_bundle_root
    assert reopened.get_subject_state(item.snapshot.subject_id) == item.commit_state


def test_second_execution_is_blocked_by_durable_terminal_uniqueness(tmp_path):
    item = policy_enabled_input()
    store = initialized_store(tmp_path / "oma.db", item)
    first = execute_composed_pipeline(item, store)
    second = execute_composed_pipeline(
        replace(item, commit_token=replace(item.commit_token, token_id="token-2"), terminal_commit_id="terminal-2"),
        store,
    )
    assert first.result.decision is ValidationDecision.ACCEPT
    assert by_node(second)["atomic_commit"].decision is ValidationDecision.BLOCK
    assert second.result.decision is ValidationDecision.BLOCK
    assert store.count() == 1


def test_authoritative_forward_drift_is_stale_even_if_caller_supplies_old_current(tmp_path):
    item = policy_enabled_input()
    store = initialized_store(tmp_path / "oma.db", item)
    advanced = replace(
        item.commit_state,
        subject_state_id="state-2",
        state_version=item.commit_state.state_version + 1,
        ledger_head="ledger-2",
    )
    update = store.advance_subject_state(item.commit_state.state_version, advanced)
    assert update.decision is SubjectStateDecision.WRITTEN

    lied = replace(item, commit_state=item.commit_state)
    result = execute_composed_pipeline(lied, store)
    assert result.result.decision is ValidationDecision.STALE
    assert by_node(result)["snapshot_freshness"].decision is ValidationDecision.STALE
    assert store.count() == 0


def test_caller_supplied_fake_newer_state_does_not_override_authoritative_state(tmp_path):
    item = policy_enabled_input()
    store = initialized_store(tmp_path / "oma.db", item)
    fake = replace(item.commit_state, state_version=99, subject_state_id="fake")
    result = execute_composed_pipeline(replace(item, commit_state=fake), store)
    assert result.result.decision is ValidationDecision.ACCEPT
    assert store.count() == 1


def test_blocked_prerequisite_never_writes_database(tmp_path):
    item = policy_enabled_input()
    item = replace(item, terminal_action="FORCE_COMMIT")
    store = initialized_store(tmp_path / "oma.db", item)
    result = execute_composed_pipeline(item, store)
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0


def test_missing_authoritative_state_cannot_commit(tmp_path):
    item = policy_enabled_input()
    path = tmp_path / "oma.db"
    SQLiteRetryLedger(path).initialize(item.retry_policy, item.retry_domain, item.retry_events[0])
    store = SQLiteTerminalStore(path)
    result = execute_composed_pipeline(item, store)
    assert by_node(result)["atomic_commit"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0


def test_missing_authoritative_retry_history_cannot_commit(tmp_path):
    item = policy_enabled_input()
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    assert store.initialize_subject_state(item.commit_state).decision is SubjectStateDecision.WRITTEN
    result = execute_composed_pipeline(item, store)
    assert by_node(result)["atomic_commit"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0
