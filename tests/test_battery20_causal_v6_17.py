from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def _state(version, state_id):
    return CommitState("s", state_id, "policy", "ob", "ev", "ledger", version, 1)


def test_17_stale_writer_conflicts_after_restart(tmp_path):
    path = tmp_path / "oma.db"
    store = SQLiteTerminalStore(path)
    assert store.initialize_subject_state(_state(1, "state-1")).decision is SubjectStateDecision.WRITTEN
    first = SQLiteTerminalStore(path)
    second = SQLiteTerminalStore(path)
    assert first.advance_subject_state(1, _state(2, "state-2")).decision is SubjectStateDecision.WRITTEN
    assert second.advance_subject_state(1, _state(2, "state-2-alt")).decision is SubjectStateDecision.CONFLICT
