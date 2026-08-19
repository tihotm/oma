from oma.commit import AcceptanceSnapshot, CommitDecision, CommitState, CommitToken, evaluate_commit


def test_19_already_finalized_state_conflicts():
    snapshot = AcceptanceSnapshot("snap", "subject", "state", "bundle", "ob", "ev", "ledger", 1, 1, "bundle-root")
    state = CommitState("subject", "state", "bundle", "ob", "ev", "ledger", 1, 1, terminal_commit_ids=frozenset({"terminal-old"}), policy_bundle_root="bundle-root")
    token = CommitToken("token", "snap", "subject", 1)
    result = evaluate_commit(snapshot, token, state, terminal_commit_id="terminal-new")
    assert result.decision is CommitDecision.CONFLICT
    assert "terminal_already_committed" in result.reasons
