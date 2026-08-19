from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def test_newline_subject_id_is_persisted():
    store=SQLiteTerminalStore(tmp_path/"oma.db")
    state=CommitState("s\n1","st","pb","o","e","l",1,1)
    assert store.initialize_subject_state(state).decision is SubjectStateDecision.WRITTEN
    assert store.get_subject_state("s\n1") is not None
