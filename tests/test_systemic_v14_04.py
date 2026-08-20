from pathlib import Path
import runpy
import sqlite3

from oma.execution import execute_composed_pipeline
from oma.sqlite_commit import SQLiteTerminalStore
from oma.validation import ValidationDecision

_helpers = runpy.run_path(str(Path(__file__).with_name("test_execution.py")))
policy_enabled_input = _helpers["policy_enabled_input"]
initialized_store = _helpers["initialized_store"]
by_node = _helpers["by_node"]


class FailingInsertStore(SQLiteTerminalStore):
    def _insert_terminal(self, *args, **kwargs):
        raise sqlite3.OperationalError("injected durable write failure")


def test_durable_write_failure_blocks_and_rolls_back(tmp_path):
    item = policy_enabled_input()
    path = tmp_path / "oma.db"
    initialized_store(path, item)
    result = execute_composed_pipeline(item, FailingInsertStore(path))
    assert by_node(result)["atomic_commit"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK
    assert SQLiteTerminalStore(path).count() == 0
