from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def _state(subject, version):
    return CommitState(subject, f"{subject}-state-{version}", "policy", "ob", "ev", "ledger", version, 1)


def test_20_subject_state_isolation_survives_restart(tmp_path):
    path = tmp_path / "oma.db"
    store = SQLiteTerminalStore(path)
    assert store.initialize_subject_state(_state("s1", 1)).decision is SubjectStateDecision.WRITTEN
    assert store.initialize_subject_state(_state("s2", 1)).decision is SubjectStateDecision.WRITTEN
    reopened = SQLiteTerminalStore(path)
    assert reopened.advance_subject_state(1, _state("s2", 2)).decision is SubjectStateDecision.WRITTEN
    assert reopened.get_subject_state("s1") == _state("s1", 1)
