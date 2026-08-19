from dataclasses import replace
from pathlib import Path
import runpy

from oma.authority_registry import AuthorityRegistryDecision, SQLiteAuthorityRegistry
from oma.execution import execute_composed_pipeline
from oma.retry_ledger import RetryLedgerDecision, SQLiteRetryLedger
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision
from oma.validation import ValidationDecision


_policy_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline_policy.py")))
policy_enabled_input = _policy_tests["policy_enabled_input"]


def initialized_store(path, item):
    store = SQLiteTerminalStore(path)
    assert store.initialize_subject_state(item.commit_state).decision is SubjectStateDecision.WRITTEN
    assert SQLiteRetryLedger(path).initialize(
        item.retry_policy, item.retry_domain, item.retry_events[0]
    ).decision is RetryLedgerDecision.WRITTEN
    assert SQLiteAuthorityRegistry(path).initialize_context(
        item.authority_context, item.capabilities
    ).decision is AuthorityRegistryDecision.WRITTEN
    return store


def by_node(result):
    return {item.node_id: item for item in result.observations}


def test_distinct_durable_commit_identity_changes_atomic_and_final_closure_roots(tmp_path):
    first_item = policy_enabled_input()
    first_store = initialized_store(tmp_path / "first.db", first_item)
    first = execute_composed_pipeline(first_item, first_store)
    assert first.result.decision is ValidationDecision.ACCEPT

    second_item = replace(
        policy_enabled_input(),
        commit_token=replace(policy_enabled_input().commit_token, token_id="token-2"),
        terminal_commit_id="terminal-2",
    )
    second_store = initialized_store(tmp_path / "second.db", second_item)
    second = execute_composed_pipeline(second_item, second_store)
    assert second.result.decision is ValidationDecision.ACCEPT

    assert by_node(first)["atomic_commit"].evidence_root != by_node(second)["atomic_commit"].evidence_root
    assert first.result.validation_closure_digest != second.result.validation_closure_digest


def test_same_commit_identity_is_deterministic_across_independent_stores(tmp_path):
    first_item = policy_enabled_input()
    first_store = initialized_store(tmp_path / "first.db", first_item)
    first = execute_composed_pipeline(first_item, first_store)

    second_item = policy_enabled_input()
    second_store = initialized_store(tmp_path / "second.db", second_item)
    second = execute_composed_pipeline(second_item, second_store)

    assert first.result.decision is ValidationDecision.ACCEPT
    assert second.result.decision is ValidationDecision.ACCEPT
    assert by_node(first)["atomic_commit"].evidence_root == by_node(second)["atomic_commit"].evidence_root
    assert first.result.validation_closure_digest == second.result.validation_closure_digest
