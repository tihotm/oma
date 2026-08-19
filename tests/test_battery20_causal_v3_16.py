from dataclasses import replace
from oma.commit import AcceptanceSnapshot, CommitDecision, CommitState, CommitToken, evaluate_commit


def _facts():
    snapshot = AcceptanceSnapshot("snap", "subject", "state", "bundle", "ob", "ev", "ledger", 1, 1, "bundle-root")
    state = CommitState("subject", "state", "bundle", "ob", "ev", "ledger", 1, 1, policy_bundle_root="bundle-root")
    token = CommitToken("token", "snap", "subject", 1)
    return snapshot, state, token


def test_16_token_snapshot_substitution_blocks():
    snapshot, state, token = _facts()
    result = evaluate_commit(snapshot, replace(token, acceptance_snapshot_id="other"), state, terminal_commit_id="terminal")
    assert result.decision is CommitDecision.BLOCK
    assert "token_snapshot_mismatch" in result.reasons
