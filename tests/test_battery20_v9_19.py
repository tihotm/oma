from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def test_newline_policy_bundle_id_is_accepted_on_update(tmp_path):
    store=SQLiteTerminalStore(tmp_path/"oma.db")
    current=CommitState("s","st1","pb","o","e","l",1,1)
    next_state=CommitState("s","st2","pb\n2","o","e","l",2,1)
    store.initialize_subject_state(current)
    assert store.advance_subject_state(1,next_state).decision is SubjectStateDecision.WRITTEN
