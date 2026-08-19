from oma.authority import AuthorityContext, Capability
from oma.authority_registry import SQLiteAuthorityRegistry, AuthorityRegistryDecision


def test_grandchild_subset_delegation_persists(tmp_path):
    r=SQLiteAuthorityRegistry(tmp_path/"oma.db")
    c=AuthorityContext("auth",1,1,frozenset({"root"}))
    root=Capability("r","root","agent",frozenset({"read","commit"}),frozenset({"s"}),frozenset({"repo"}),1,0,10)
    child=Capability("c","agent","worker",frozenset({"read"}),frozenset({"s"}),frozenset({"repo"}),1,0,9,"r")
    grand=Capability("g","worker","leaf",frozenset({"read"}),frozenset({"s"}),frozenset({"repo"}),1,0,8,"c")
    assert r.initialize_context(c,(root,)).decision is AuthorityRegistryDecision.WRITTEN
    assert r.issue(c,child).decision is AuthorityRegistryDecision.WRITTEN
    assert r.issue(c,grand).decision is AuthorityRegistryDecision.WRITTEN
