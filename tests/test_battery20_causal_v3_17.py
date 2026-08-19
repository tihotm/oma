from dataclasses import replace
from oma.commit import AcceptanceSnapshot, CommitDecision, CommitState, CommitToken, evaluate_commit


def test_17_snapshot_state_drift_is_stale():
    snapshot = AcceptanceSnapshot("snap", "subject", "state", "bundle", "ob", "ev", "ledger", 1, 1, "bundle-root")
    state = CommitState("subject", "state", "bundle", "ob", "ev", "ledger", 1, 1, policy_bundle_root="bundle-root")
    token = CommitToken("token", "snap", "subject", 1)
    result = evaluate_commit(snapshot, token, replace(state, state_version=2), terminal_commit_id="terminal")
    assert result.decision is CommitDecision.STALE
    assert "snapshot_drift:state_version" in result.reasons
