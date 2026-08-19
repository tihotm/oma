from oma.authority import AuthorityContext, Capability
from oma.authority_registry import SQLiteAuthorityRegistry, AuthorityRegistryDecision


def test_now_epoch_can_advance_without_invalidating_registry_binding(tmp_path):
    r=SQLiteAuthorityRegistry(tmp_path/"oma.db")
    c=AuthorityContext("auth",1,1,frozenset({"root"}))
    cap=Capability("root-cap","root","agent",frozenset({"read"}),frozenset({"s"}),frozenset({"repo"}),1,0,10)
    assert r.initialize_context(c,(cap,)).decision is AuthorityRegistryDecision.WRITTEN
    later=AuthorityContext("auth",1,5,frozenset({"root"}))
    assert r.get(later)==(cap,)
