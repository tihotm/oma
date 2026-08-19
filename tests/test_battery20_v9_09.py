from oma.commit import AcceptanceSnapshot, CommitDecision, CommitState, CommitToken, evaluate_commit


def test_state_version_forward_drift_is_stale():
    s=AcceptanceSnapshot("snap","s","st","pb","o","e","l",1,1)
    t=CommitToken("tok","snap","s",1)
    c=CommitState("s","st","pb","o","e","l",2,1)
    assert evaluate_commit(s,t,c,terminal_commit_id="commit").decision is CommitDecision.STALE
