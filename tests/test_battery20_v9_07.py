from oma.commit import AcceptanceSnapshot, CommitDecision, CommitState, CommitToken, evaluate_commit


def test_boolean_token_epoch_matches_integer_snapshot_epoch():
    s=AcceptanceSnapshot("snap","s","st","pb","o","e","l",1,1)
    t=CommitToken("tok","snap","s",True)
    c=CommitState("s","st","pb","o","e","l",1,1)
    assert evaluate_commit(s,t,c,terminal_commit_id="commit").decision is CommitDecision.ALLOW
