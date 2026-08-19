from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def test_terminal_epoch_rollback_is_blocked(tmp_path):
    store=SQLiteTerminalStore(tmp_path/"oma.db")
    current=CommitState("s","st1","pb","o","e","l",1,2)
    next_state=CommitState("s","st2","pb","o","e","l",2,1)
    store.initialize_subject_state(current)
    assert store.advance_subject_state(1,next_state).decision is SubjectStateDecision.BLOCK
