from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


def test_v12_12_trailing_dot_forbidden_alias_currently_allows():
    policy = ScopePolicy("scope:v1", allowed_paths=("src",), forbidden_paths=("src/secret",))
    transition = FileTransition("src/secret.", "before", "after")
    assert evaluate_scope(policy, (transition,)).decision is ScopeDecision.ALLOW
