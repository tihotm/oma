from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def test_integral_float_next_state_version_is_accepted(tmp_path):
    store=SQLiteTerminalStore(tmp_path/"oma.db")
    current=CommitState("s","st1","pb","o","e","l",1,1)
    next_state=CommitState("s","st2","pb","o","e","l",2.0,1)
    store.initialize_subject_state(current)
    assert store.advance_subject_state(1,next_state).decision is SubjectStateDecision.WRITTEN
    assert store.get_subject_state("s").state_version == 2
