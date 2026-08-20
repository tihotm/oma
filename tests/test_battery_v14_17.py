from dataclasses import replace
from oma.authority import AuthorityContext, Capability
from oma.authority_registry import SQLiteAuthorityRegistry


def test_registry_loads_same_context_under_changed_now_epoch(tmp_path):
    path=tmp_path/'a.db'
    base=AuthorityContext('ctx',1,7,frozenset({'root'}))
    cap=Capability('cap','root','agent',frozenset({'commit'}),frozenset({'subject'}),frozenset({'repo'}),1,0,10)
    reg=SQLiteAuthorityRegistry(path)
    assert reg.initialize_context(base,(cap,)).capability is None
    loaded=reg.get(replace(base,now_epoch=700))
    assert loaded is not None and loaded[0].capability_id == 'cap'
