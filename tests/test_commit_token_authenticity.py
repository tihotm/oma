from dataclasses import replace
from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.retry_ledger import RetryLedgerDecision, SQLiteRetryLedger
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision
from oma.validation import ValidationDecision


_policy_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline_policy.py")))
policy_enabled_input = _policy_tests["policy_enabled_input"]
_pipeline_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline.py")))
by_node = _pipeline_tests["by_node"]


def initialized_store(path, item):
    store = SQLiteTerminalStore(path)
    result = store.initialize_subject_state(item.commit_state)
    assert result.decision is SubjectStateDecision.WRITTEN
    assert SQLiteRetryLedger(path).initialize(
        item.retry_policy, item.retry_domain, item.retry_events[0]
    ).decision is RetryLedgerDecision.WRITTEN
    return store


def test_freely_chosen_token_id_is_not_an_authority_credential(tmp_path):
    item = policy_enabled_input()
    forged = replace(
        item,
        commit_token=replace(item.commit_token, token_id="caller-chosen-token"),
    )
    store = initialized_store(tmp_path / "oma.db", forged)

    result = execute_composed_pipeline(forged, store)

    assert by_node(result)["authority_capability"].decision is ValidationDecision.ACCEPT
    assert by_node(result)["commit_authorization"].decision is ValidationDecision.ACCEPT
    assert by_node(result)["atomic_commit"].decision is ValidationDecision.ACCEPT
    assert result.result.decision is ValidationDecision.ACCEPT
    assert store.count() == 1


def test_forged_token_cannot_replace_failed_authority(tmp_path):
    item = policy_enabled_input()
    forged = replace(
        item,
        authority_request=replace(item.authority_request, actor="attacker"),
        commit_token=replace(item.commit_token, token_id="caller-chosen-token"),
    )
    store = initialized_store(tmp_path / "oma.db", forged)

    result = execute_composed_pipeline(forged, store)

    assert by_node(result)["authority_capability"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0


def test_forged_token_cannot_replace_terminal_barrier(tmp_path):
    item = policy_enabled_input()
    forged = replace(
        item,
        terminal_action="FORCE_COMMIT",
        commit_token=replace(item.commit_token, token_id="caller-chosen-token"),
    )
    store = initialized_store(tmp_path / "oma.db", forged)

    result = execute_composed_pipeline(forged, store)

    assert by_node(result)["terminal_barrier"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0
