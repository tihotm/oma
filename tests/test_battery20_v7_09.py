from oma.authority import AuthorityContext, Capability
from oma.authority_registry import SQLiteAuthorityRegistry, AuthorityRegistryDecision


def test_expired_child_is_not_issued(tmp_path):
    r=SQLiteAuthorityRegistry(tmp_path/"oma.db")
    c=AuthorityContext("auth",1,5,frozenset({"root"}))
    root=Capability("r","root","agent",frozenset({"read"}),frozenset({"s"}),frozenset({"repo"}),1,0,10)
    child=Capability("c","agent","worker",frozenset({"read"}),frozenset({"s"}),frozenset({"repo"}),1,0,4,"r")
    assert r.initialize_context(c,(root,)).decision is AuthorityRegistryDecision.WRITTEN
    assert r.issue(c,child).decision is AuthorityRegistryDecision.BLOCK
