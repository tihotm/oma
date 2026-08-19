from oma.commit import AcceptanceSnapshot, CommitDecision, CommitState, CommitToken, evaluate_commit


def test_numeric_token_id_is_accepted():
    s=AcceptanceSnapshot("snap","s","st","pb","o","e","l",1,1)
    t=CommitToken(1,"snap","s",1)
    c=CommitState("s","st","pb","o","e","l",1,1)
    assert evaluate_commit(s,t,c,terminal_commit_id="commit").decision is CommitDecision.ALLOW
