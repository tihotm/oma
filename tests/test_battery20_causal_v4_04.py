from oma.commit import AcceptanceSnapshot, CommitState
from oma.snapshot import SnapshotDecision, evaluate_snapshot_freshness


def test_snapshot_subject_mismatch_blocks():
    snapshot = AcceptanceSnapshot("snap","s","st","p","o","e","l",2,3,"pr")
    current = CommitState("other","st","p","o","e","l",2,3,policy_bundle_root="pr")
    result = evaluate_snapshot_freshness(snapshot, current)
    assert result.decision is SnapshotDecision.BLOCK
