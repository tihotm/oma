from oma.authority import AuthorityContext, AuthorityDecision, AuthorityRequest, Capability, evaluate_authority


def test_valid_three_level_delegation_allows():
    ctx = AuthorityContext("ctx", 1, 5, frozenset({"root"}))
    root = Capability("p1", "root", "broker1", frozenset({"commit", "read"}), frozenset({"s", "t"}), frozenset({"repo", "ci"}), 1, 0, 10)
    mid = Capability("p2", "broker1", "broker2", frozenset({"commit"}), frozenset({"s"}), frozenset({"repo"}), 1, 1, 9, "p1")
    leaf = Capability("p3", "broker2", "agent", frozenset({"commit"}), frozenset({"s"}), frozenset({"repo"}), 1, 2, 8, "p2")
    req = AuthorityRequest("agent", "commit", "s", "repo", "p3")
    assert evaluate_authority(ctx, (root, mid, leaf), req).decision is AuthorityDecision.ALLOW
