from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def test_boolean_expected_version_matches_integer_current_version(tmp_path):
    store=SQLiteTerminalStore(tmp_path/"oma.db")
    current=CommitState("s","st1","pb","o","e","l",1,1)
    next_state=CommitState("s","st2","pb","o","e","l",2,1)
    assert store.initialize_subject_state(current).decision is SubjectStateDecision.WRITTEN
    assert store.advance_subject_state(True,next_state).decision is SubjectStateDecision.WRITTEN
