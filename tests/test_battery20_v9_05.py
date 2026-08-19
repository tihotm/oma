from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def test_duplicate_subject_initialization_conflicts(tmp_path):
    store=SQLiteTerminalStore(tmp_path/"oma.db")
    state=CommitState("s","st","pb","o","e","l",1,1)
    assert store.initialize_subject_state(state).decision is SubjectStateDecision.WRITTEN
    assert store.initialize_subject_state(state).decision is SubjectStateDecision.CONFLICT
