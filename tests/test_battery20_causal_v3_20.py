from oma.commit import AcceptanceSnapshot, CommitDecision, CommitState, CommitToken, commit_if_current


def test_20_commit_transition_records_token_and_terminal_id_together():
    snapshot = AcceptanceSnapshot("snap", "subject", "state", "bundle", "ob", "ev", "ledger", 1, 1, "bundle-root")
    state = CommitState("subject", "state", "bundle", "ob", "ev", "ledger", 1, 1, policy_bundle_root="bundle-root")
    token = CommitToken("token", "snap", "subject", 1)
    transition = commit_if_current(snapshot, token, state, terminal_commit_id="terminal")
    assert transition.result.decision is CommitDecision.ALLOW
    assert transition.state.consumed_token_ids == frozenset({"token"})
    assert transition.state.terminal_commit_ids == frozenset({"terminal"})
