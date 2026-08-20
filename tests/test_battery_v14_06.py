import pytest
from oma.commit import AcceptanceSnapshot, CommitState, CommitToken, commit_if_current


def base():
    s=AcceptanceSnapshot('snap','sub','state','pb','obl','ev','ledger',1,1,'root')
    t=CommitToken('tok','snap','sub',1,True)
    c=CommitState('sub','state','pb','obl','ev','ledger',1,1,[],frozenset(),'root')
    return s,t,c

def test_list_consumed_token_container_crashes_transition():
    s,t,c=base()
    with pytest.raises(TypeError):
        commit_if_current(s,t,c,terminal_commit_id='term')
