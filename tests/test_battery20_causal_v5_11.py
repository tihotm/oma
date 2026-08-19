from oma.authority import AuthorityContext, AuthorityDecision, AuthorityRequest, Capability, evaluate_authority


def test_child_cannot_outlive_parent_capability():
    ctx = AuthorityContext("ctx", 1, 5, frozenset({"root"}))
    parent = Capability("p", "root", "broker", frozenset({"commit"}), frozenset({"s"}), frozenset({"repo"}), 1, 0, 5)
    child = Capability("c", "broker", "agent", frozenset({"commit"}), frozenset({"s"}), frozenset({"repo"}), 1, 0, 6, "p")
    req = AuthorityRequest("agent", "commit", "s", "repo", "c")
    assert evaluate_authority(ctx, (parent, child), req).decision is AuthorityDecision.BLOCK
