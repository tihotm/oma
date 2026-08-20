from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.sqlite_commit import SQLiteTerminalStore
from oma.validation import ValidationDecision

_helpers = runpy.run_path(str(Path(__file__).with_name("test_execution.py")))
policy_enabled_input = _helpers["policy_enabled_input"]
initialized_store = _helpers["initialized_store"]
by_node = _helpers["by_node"]


class AuthorityRevokedBeforeCommitStore(SQLiteTerminalStore):
    def commit(self, pipeline_input):
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM authority_capabilities WHERE authority_context_id = ?",
                (pipeline_input.authority_context.authority_context_id,),
            )
        return super().commit(pipeline_input)


def test_authority_change_between_precheck_and_commit_blocks(tmp_path):
    item = policy_enabled_input()
    path = tmp_path / "oma.db"
    initialized_store(path, item)
    result = execute_composed_pipeline(item, AuthorityRevokedBeforeCommitStore(path))
    assert by_node(result)["atomic_commit"].decision is ValidationDecision.BLOCK
    assert result.result.decision is ValidationDecision.BLOCK
    assert SQLiteTerminalStore(path).count() == 0
