from oma.commit import AcceptanceSnapshot, CommitDecision, CommitState, CommitToken, commit_if_current


def test_frozenset_commit_containers_transition_cleanly():
    s=AcceptanceSnapshot('snap','sub','state','pb','obl','ev','ledger',1,1,'root')
    t=CommitToken('tok','snap','sub',1,True)
    c=CommitState('sub','state','pb','obl','ev','ledger',1,1,frozenset(),frozenset(),'root')
    out=commit_if_current(s,t,c,terminal_commit_id='term')
    assert out.result.decision is CommitDecision.ALLOW
    assert out.state.consumed_token_ids == frozenset({'tok'})
    assert out.state.terminal_commit_ids == frozenset({'term'})
