from oma.commit import AcceptanceSnapshot, CommitState
from oma.snapshot import SnapshotDecision, evaluate_snapshot_freshness


def test_subject_mismatch_is_blocked():
    s=AcceptanceSnapshot("snap","s1","st","pb","o","e","l",1,1)
    c=CommitState("s2","st","pb","o","e","l",1,1)
    assert evaluate_snapshot_freshness(s,c).decision is SnapshotDecision.BLOCK
