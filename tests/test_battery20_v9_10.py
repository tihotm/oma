from oma.commit import AcceptanceSnapshot, CommitDecision, CommitState, CommitToken, evaluate_commit


def test_consumed_token_replay_conflicts():
    s=AcceptanceSnapshot("snap","s","st","pb","o","e","l",1,1)
    t=CommitToken("tok","snap","s",1)
    c=CommitState("s","st","pb","o","e","l",1,1,consumed_token_ids=frozenset({"tok"}))
    assert evaluate_commit(s,t,c,terminal_commit_id="commit").decision is CommitDecision.CONFLICT
