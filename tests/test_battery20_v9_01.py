from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def test_numeric_subject_id_is_coerced_into_text_identity(tmp_path):
    store=SQLiteTerminalStore(tmp_path/"oma.db")
    state=CommitState(1,"st","pb","o","e","l",1,1)
    assert store.initialize_subject_state(state).decision is SubjectStateDecision.WRITTEN
    assert store.get_subject_state("1") is not None
