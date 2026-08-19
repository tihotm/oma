from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def _state(version=1, epoch=1):
    return CommitState("s", f"state-{version}", "policy", "ob", "ev", "ledger", version, epoch)


def test_16_subject_state_survives_store_reopen(tmp_path):
    path = tmp_path / "oma.db"
    first = SQLiteTerminalStore(path)
    assert first.initialize_subject_state(_state()).decision is SubjectStateDecision.WRITTEN
    reopened = SQLiteTerminalStore(path)
    assert reopened.get_subject_state("s") == _state()
