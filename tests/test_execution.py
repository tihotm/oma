from dataclasses import replace
from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.sqlite_commit import SQLiteTerminalStore
from oma.validation import ValidationDecision


_policy_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline_policy.py")))
policy_enabled_input = _policy_tests["policy_enabled_input"]
by_node = runpy.run_path(str(Path(__file__).with_name("test_pipeline.py")))["by_node"]


def test_fully_valid_pipeline_commits_durably_and_accepts(tmp_path):
    item = policy_enabled_input()
    store = SQLiteTerminalStore(tmp_path / "oma.db")
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
    result = execute_composed_pipeline(item, SQLiteTerminalStore(path))
    assert result.result.decision is ValidationDecision.ACCEPT
    reopened = SQLiteTerminalStore(path)
    record = reopened.get(item.terminal_commit_id)
    assert record is not None
    assert record.acceptance_snapshot_id == item.snapshot.acceptance_snapshot_id
    assert record.policy_bundle_root == item.snapshot.policy_bundle_root


def test_second_execution_is_blocked_by_durable_terminal_uniqueness(tmp_path):
    item = policy_enabled_input()
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    first = execute_composed_pipeline(item, store)
    second = execute_composed_pipeline(
        replace(item, commit_token=replace(item.commit_token, token_id="token-2"), terminal_commit_id="terminal-2"),
        store,
    )
    assert first.result.decision is ValidationDecision.ACCEPT
    assert by_node(second)["atomic_commit"].decision is ValidationDecision.BLOCK
    assert second.result.decision is ValidationDecision.BLOCK
    assert store.count() == 1


def test_stale_prerequisite_never_writes_database(tmp_path):
    item = policy_enabled_input()
    item = replace(item, commit_state=replace(item.commit_state, state_version=2))
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    result = execute_composed_pipeline(item, store)
    assert result.result.decision is ValidationDecision.STALE
    assert store.count() == 0


def test_blocked_prerequisite_never_writes_database(tmp_path):
    item = policy_enabled_input()
    item = replace(item, terminal_action="FORCE_COMMIT")
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    result = execute_composed_pipeline(item, store)
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0
