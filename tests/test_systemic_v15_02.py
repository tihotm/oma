from dataclasses import replace
from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.sqlite_commit import SubjectStateDecision
from oma.validation import ValidationDecision

_helpers = runpy.run_path(str(Path(__file__).with_name("test_execution.py")))
policy_enabled_input = _helpers["policy_enabled_input"]
initialized_store = _helpers["initialized_store"]


def test_terminal_commit_freezes_subject_state_within_same_epoch(tmp_path):
    item = policy_enabled_input()
    store = initialized_store(tmp_path / "oma.db", item)
    committed = execute_composed_pipeline(item, store)
    assert committed.result.decision is ValidationDecision.ACCEPT
    next_state = replace(
        item.commit_state,
        subject_state_id="state-after-terminal",
        ledger_head="ledger-after-terminal",
        state_version=item.commit_state.state_version + 1,
    )
    result = store.advance_subject_state(item.commit_state.state_version, next_state)
    assert result.decision is SubjectStateDecision.BLOCK
