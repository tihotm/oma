from oma.commit import AcceptanceSnapshot, CommitState
from oma.snapshot import SnapshotDecision, evaluate_snapshot_freshness


def test_boolean_snapshot_state_version_equals_integer_current_version():
    s=AcceptanceSnapshot("snap","s","st","pb","o","e","l",True,1)
    c=CommitState("s","st","pb","o","e","l",1,1)
    assert evaluate_snapshot_freshness(s,c).decision is SnapshotDecision.ALLOW
