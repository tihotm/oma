from oma.commit import AcceptanceSnapshot, CommitDecision, CommitState, CommitToken, evaluate_commit


def test_18_consumed_token_replay_conflicts():
    snapshot = AcceptanceSnapshot("snap", "subject", "state", "bundle", "ob", "ev", "ledger", 1, 1, "bundle-root")
    state = CommitState("subject", "state", "bundle", "ob", "ev", "ledger", 1, 1, consumed_token_ids=frozenset({"token"}), policy_bundle_root="bundle-root")
    token = CommitToken("token", "snap", "subject", 1)
    result = evaluate_commit(snapshot, token, state, terminal_commit_id="terminal")
    assert result.decision is CommitDecision.CONFLICT
    assert "commit_token_replay" in result.reasons
