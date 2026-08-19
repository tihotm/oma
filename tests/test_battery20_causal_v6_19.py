from oma.commit import CommitState
from oma.sqlite_commit import SQLiteTerminalStore, SubjectStateDecision


def _state(version, epoch):
    return CommitState("s", f"state-{version}", "policy", "ob", "ev", "ledger", version, epoch)


def test_19_terminal_epoch_rollback_blocks_after_restart(tmp_path):
    path = tmp_path / "oma.db"
    store = SQLiteTerminalStore(path)
    assert store.initialize_subject_state(_state(1, 2)).decision is SubjectStateDecision.WRITTEN
    reopened = SQLiteTerminalStore(path)
    assert reopened.advance_subject_state(1, _state(2, 1)).decision is SubjectStateDecision.BLOCK
