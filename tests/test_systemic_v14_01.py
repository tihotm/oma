from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.sqlite_commit import SQLiteTerminalStore
from oma.validation import ValidationDecision

_helpers = runpy.run_path(str(Path(__file__).with_name("test_execution.py")))
policy_enabled_input = _helpers["policy_enabled_input"]
initialized_store = _helpers["initialized_store"]


def test_concurrent_terminalization_admits_exactly_one_commit(tmp_path):
    item = policy_enabled_input()
    path = tmp_path / "oma.db"
    initialized_store(path, item)

    def run(token_id, terminal_id):
        candidate = replace(
            item,
            commit_token=replace(item.commit_token, token_id=token_id),
            terminal_commit_id=terminal_id,
        )
        return execute_composed_pipeline(candidate, SQLiteTerminalStore(path)).result.decision

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda args: run(*args), (("token-a", "terminal-a"), ("token-b", "terminal-b"))))

    assert results.count(ValidationDecision.ACCEPT) == 1
    assert results.count(ValidationDecision.BLOCK) == 1
    assert SQLiteTerminalStore(path).count() == 1
