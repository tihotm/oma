from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def test_boolean_terminal_epoch_is_persisted_as_integer(tmp_path):
    store=SQLiteTerminalStore(tmp_path/"oma.db")
    state=CommitState("s","st","pb","o","e","l",1,True)
    assert store.initialize_subject_state(state).decision is SubjectStateDecision.WRITTEN
    assert store.get_subject_state("s").terminal_epoch == 1
