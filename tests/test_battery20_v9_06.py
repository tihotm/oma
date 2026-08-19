from oma.commit import AcceptanceSnapshot, CommitDecision, CommitState, CommitToken, evaluate_commit


def test_integer_one_is_accepted_as_single_use_flag():
    s=AcceptanceSnapshot("snap","s","st","pb","o","e","l",1,1)
    t=CommitToken("tok","snap","s",1,single_use=1)
    c=CommitState("s","st","pb","o","e","l",1,1)
    assert evaluate_commit(s,t,c,terminal_commit_id="commit").decision is CommitDecision.ALLOW
