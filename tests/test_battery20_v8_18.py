from oma.commit import AcceptanceSnapshot, CommitState
from oma.snapshot import SnapshotDecision, evaluate_snapshot_freshness


def test_newline_subject_id_is_accepted_when_both_sides_match():
    s=AcceptanceSnapshot("snap","s\n1","st","pb","o","e","l",1,1)
    c=CommitState("s\n1","st","pb","o","e","l",1,1)
    assert evaluate_snapshot_freshness(s,c).decision is SnapshotDecision.ALLOW
