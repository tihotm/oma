from oma.authority import AuthorityContext, Capability
from oma.authority_registry import SQLiteAuthorityRegistry, AuthorityRegistryDecision


def test_different_trusted_issuer_sets_can_read_same_registry_via_newline_collision(tmp_path):
    r=SQLiteAuthorityRegistry(tmp_path/"oma.db")
    original=AuthorityContext("auth",1,1,frozenset({"a","b"}))
    cap=Capability("root","a","agent",frozenset({"read"}),frozenset({"s"}),frozenset({"repo"}),1,0,10)
    assert r.initialize_context(original,(cap,)).decision is AuthorityRegistryDecision.WRITTEN
    collided=AuthorityContext("auth",1,1,frozenset({"a\nb"}))
    assert r.get(collided)==(cap,)
