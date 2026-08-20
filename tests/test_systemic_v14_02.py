from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import runpy

from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision

_helpers = runpy.run_path(str(Path(__file__).with_name("test_execution.py")))
policy_enabled_input = _helpers["policy_enabled_input"]


def test_concurrent_subject_state_cas_admits_exactly_one_writer(tmp_path):
    item = policy_enabled_input()
    path = tmp_path / "oma.db"
    store = SQLiteTerminalStore(path)
    assert store.initialize_subject_state(item.commit_state).decision is SubjectStateDecision.WRITTEN
    v = item.commit_state.state_version
    next_a = replace(item.commit_state, subject_state_id="state-a", ledger_head="ledger-a", state_version=v + 1)
    next_b = replace(item.commit_state, subject_state_id="state-b", ledger_head="ledger-b", state_version=v + 1)

    def advance(next_state):
        return SQLiteTerminalStore(path).advance_subject_state(v, next_state).decision

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(advance, (next_a, next_b)))

    assert results.count(SubjectStateDecision.WRITTEN) == 1
    assert results.count(SubjectStateDecision.CONFLICT) == 1
    final = SQLiteTerminalStore(path).get_subject_state(item.commit_state.subject_id)
    assert final is not None and final.state_version == v + 1
