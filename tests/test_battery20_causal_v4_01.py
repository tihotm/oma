from dataclasses import replace
from oma.commit import AcceptanceSnapshot, CommitState
from oma.snapshot import SnapshotDecision, evaluate_snapshot_freshness


def _pair():
    snapshot = AcceptanceSnapshot("snap","s","st","p","o","e","l",2,3,"pr")
    current = CommitState("s","st","p","o","e","l",2,3,policy_bundle_root="pr")
    return snapshot, current


def test_snapshot_state_version_rollback_blocks():
    snapshot, current = _pair()
    result = evaluate_snapshot_freshness(snapshot, replace(current, state_version=1))
    assert result.decision is SnapshotDecision.BLOCK
