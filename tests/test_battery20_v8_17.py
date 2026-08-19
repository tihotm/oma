from oma.commit import AcceptanceSnapshot, CommitState
from oma.snapshot import SnapshotDecision, evaluate_snapshot_freshness


def test_boolean_snapshot_terminal_epoch_equals_integer_current_epoch():
    s=AcceptanceSnapshot("snap","s","st","pb","o","e","l",1,True)
    c=CommitState("s","st","pb","o","e","l",1,1)
    assert evaluate_snapshot_freshness(s,c).decision is SnapshotDecision.ALLOW
