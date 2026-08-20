from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.sqlite_commit import SQLiteTerminalStore
from oma.validation import ValidationDecision

_helpers = runpy.run_path(str(Path(__file__).with_name("test_execution.py")))
policy_enabled_input = _helpers["policy_enabled_input"]
initialized_store = _helpers["initialized_store"]
by_node = _helpers["by_node"]


def test_replay_after_store_reopen_remains_blocked(tmp_path):
    item = policy_enabled_input()
    path = tmp_path / "oma.db"
    first_store = initialized_store(path, item)
    first = execute_composed_pipeline(item, first_store)
    assert first.result.decision is ValidationDecision.ACCEPT

    reopened = SQLiteTerminalStore(path)
    second = execute_composed_pipeline(item, reopened)
    assert by_node(second)["atomic_commit"].decision is ValidationDecision.BLOCK
    assert second.result.decision is ValidationDecision.BLOCK
    assert reopened.count() == 1
