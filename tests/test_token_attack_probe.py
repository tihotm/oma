from dataclasses import replace
from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.sqlite_commit import SQLiteTerminalStore
from oma.validation import ValidationDecision


_policy_tests = runpy.run_path(str(Path(__file__).with_name("test_pipeline_policy.py")))
policy_enabled_input = _policy_tests["policy_enabled_input"]


def test_forged_but_well_bound_token_currently_commits(tmp_path):
    item = policy_enabled_input()
    forged = replace(item.commit_token, token_id="attacker-invented-token")
    item = replace(item, commit_token=forged)
    store = SQLiteTerminalStore(tmp_path / "oma.db")
    store.initialize_subject_state(item.commit_state)

    result = execute_composed_pipeline(item, store)

    assert result.result.decision is ValidationDecision.ACCEPT
    record = store.get(item.terminal_commit_id)
    assert record is not None
    assert record.token_id == "attacker-invented-token"
