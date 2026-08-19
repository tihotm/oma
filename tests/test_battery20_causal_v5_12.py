from oma.authority import AuthorityContext, AuthorityDecision, AuthorityRequest, Capability, evaluate_authority


def test_child_cannot_become_valid_before_parent():
    ctx = AuthorityContext("ctx", 1, 5, frozenset({"root"}))
    parent = Capability("p", "root", "broker", frozenset({"commit"}), frozenset({"s"}), frozenset({"repo"}), 1, 5, 10)
    child = Capability("c", "broker", "agent", frozenset({"commit"}), frozenset({"s"}), frozenset({"repo"}), 1, 4, 10, "p")
    req = AuthorityRequest("agent", "commit", "s", "repo", "c")
    assert evaluate_authority(ctx, (parent, child), req).decision is AuthorityDecision.BLOCK
