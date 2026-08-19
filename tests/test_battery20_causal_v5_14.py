from oma.authority import AuthorityContext, AuthorityDecision, AuthorityRequest, Capability, evaluate_authority


def test_missing_parent_capability_blocks():
    ctx = AuthorityContext("ctx", 1, 1, frozenset({"root"}))
    child = Capability("c", "broker", "agent", frozenset({"commit"}), frozenset({"s"}), frozenset({"repo"}), 1, 0, 10, "missing")
    req = AuthorityRequest("agent", "commit", "s", "repo", "c")
    assert evaluate_authority(ctx, (child,), req).decision is AuthorityDecision.BLOCK
