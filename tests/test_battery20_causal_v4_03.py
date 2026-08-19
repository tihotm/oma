from dataclasses import replace
from oma.commit import AcceptanceSnapshot, CommitState
from oma.snapshot import SnapshotDecision, evaluate_snapshot_freshness


def test_snapshot_policy_root_drift_is_stale():
    snapshot = AcceptanceSnapshot("snap","s","st","p","o","e","l",2,3,"pr")
    current = CommitState("s","st","p","o","e","l",2,3,policy_bundle_root="other")
    result = evaluate_snapshot_freshness(snapshot, current)
    assert result.decision is SnapshotDecision.STALE
