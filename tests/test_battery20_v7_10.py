from oma.authority import AuthorityContext, Capability
from oma.authority_registry import SQLiteAuthorityRegistry, AuthorityRegistryDecision


def test_tab_control_in_capability_id_is_accepted(tmp_path):
    r=SQLiteAuthorityRegistry(tmp_path/"oma.db")
    c=AuthorityContext("auth",1,1,frozenset({"root"}))
    cap=Capability("root\tcap","root","agent",frozenset({"read"}),frozenset({"s"}),frozenset({"repo"}),1,0,10)
    assert r.initialize_context(c,(cap,)).decision is AuthorityRegistryDecision.WRITTEN
