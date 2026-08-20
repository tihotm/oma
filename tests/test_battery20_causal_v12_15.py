from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


def test_v12_15_backslash_traversal_still_blocks():
    policy = ScopePolicy("scope:v1", allowed_paths=("src",))
    transition = FileTransition("src\\..\\secret", "before", "after")
    assert evaluate_scope(policy, (transition,)).decision is ScopeDecision.BLOCK
