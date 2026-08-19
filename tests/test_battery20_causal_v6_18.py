from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def _state(version):
    return CommitState("s", f"state-{version}", "policy", "ob", "ev", "ledger", version, 1)


def test_18_legitimate_advance_survives_restart(tmp_path):
    path = tmp_path / "oma.db"
    store = SQLiteTerminalStore(path)
    assert store.initialize_subject_state(_state(1)).decision is SubjectStateDecision.WRITTEN
    reopened = SQLiteTerminalStore(path)
    assert reopened.advance_subject_state(1, _state(2)).decision is SubjectStateDecision.WRITTEN
    again = SQLiteTerminalStore(path)
    assert again.get_subject_state("s") == _state(2)
