from dataclasses import replace
from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.retry import RetryEvent, RetryEventKind
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
    return store


def exhausted_history(item):
    first = item.retry_events[0]
    second = RetryEvent(
        event_id="event-2",
        sequence=2,
        kind=RetryEventKind.RETRY,
        attempt_number=2,
        run_id="run-2",
        subject_id=first.subject_id,
        pair_id=first.pair_id,
        lineage_id=first.lineage_id,
        retry_domain_id=first.retry_domain_id,
        retry_policy_id=first.retry_policy_id,
        reason="verification_failed",
        cost_units=first.cost_units,
    )
    return (first, second)


def test_complete_exhausted_retry_history_blocks_new_terminalization(tmp_path):
    item = policy_enabled_input()
    item = replace(item, retry_events=exhausted_history(item))
    store = initialized_store(tmp_path / "complete.db", item)

    result = execute_composed_pipeline(item, store)

    assert by_node(result)["retry_recovery"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0


def test_omitting_historical_retry_can_reopen_acceptance_path(tmp_path):
    item = policy_enabled_input()
    # The complete factual history would contain an exhausted second attempt,
    # but the supported execution boundary accepts the caller-supplied tuple.
    omitted = replace(item, retry_events=(item.retry_events[0],))
    store = initialized_store(tmp_path / "omitted.db", omitted)

    result = execute_composed_pipeline(omitted, store)

    assert by_node(result)["retry_recovery"].decision is ValidationDecision.ACCEPT
    assert result.result.decision is ValidationDecision.ACCEPT
    assert store.count() == 1
