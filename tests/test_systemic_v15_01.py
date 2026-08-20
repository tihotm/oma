from dataclasses import replace
from pathlib import Path
import runpy

from oma.execution import execute_composed_pipeline
from oma.validation import ValidationDecision

_helpers = runpy.run_path(str(Path(__file__).with_name("test_execution.py")))
policy_enabled_input = _helpers["policy_enabled_input"]
initialized_store = _helpers["initialized_store"]


def test_unissued_caller_chosen_commit_token_cannot_terminalize(tmp_path):
    item = policy_enabled_input()
    forged = replace(item, commit_token=replace(item.commit_token, token_id="caller-forged-token"))
    store = initialized_store(tmp_path / "oma.db", forged)
    result = execute_composed_pipeline(forged, store)
    assert result.result.decision is ValidationDecision.BLOCK
    assert store.count() == 0
