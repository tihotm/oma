from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.retry import RetryEvent, RetryEventKind
from oma.retry_ledger import RetryLedgerDecision, SQLiteRetryLedger
from oma.validation import ValidationDecision

_helpers = runpy.run_path(str(Path(__file__).with_name("test_execution.py")))
policy_enabled_input = _helpers["policy_enabled_input"]
initialized_store = _helpers["initialized_store"]


def test_terminal_commit_freezes_retry_domain(tmp_path):
    item = policy_enabled_input()
    path = tmp_path / "oma.db"
    store = initialized_store(path, item)
    committed = execute_composed_pipeline(item, store)
    assert committed.result.decision is ValidationDecision.ACCEPT
    first = item.retry_events[0]
    retry = RetryEvent(
        event_id="event-after-terminal",
        sequence=2,
        kind=RetryEventKind.RETRY,
        attempt_number=2,
        run_id=first.run_id,
        subject_id=first.subject_id,
        pair_id=first.pair_id,
        lineage_id=first.lineage_id,
        retry_domain_id=first.retry_domain_id,
        retry_policy_id=first.retry_policy_id,
        reason="verification_failed",
        cost_units=1,
    )
    result = SQLiteRetryLedger(path).append(item.retry_policy, item.retry_domain, retry)
    assert result.decision in {RetryLedgerDecision.BLOCK, RetryLedgerDecision.CONFLICT}
