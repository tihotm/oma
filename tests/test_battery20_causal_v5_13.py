from oma.authority import AuthorityContext, AuthorityDecision, AuthorityRequest, Capability, evaluate_authority


def test_expired_parent_makes_child_stale():
    ctx = AuthorityContext("ctx", 1, 6, frozenset({"root"}))
    parent = Capability("p", "root", "broker", frozenset({"commit"}), frozenset({"s"}), frozenset({"repo"}), 1, 0, 5)
    child = Capability("c", "broker", "agent", frozenset({"commit"}), frozenset({"s"}), frozenset({"repo"}), 1, 0, 5, "p")
    req = AuthorityRequest("agent", "commit", "s", "repo", "c")
    assert evaluate_authority(ctx, (parent, child), req).decision is AuthorityDecision.STALE
