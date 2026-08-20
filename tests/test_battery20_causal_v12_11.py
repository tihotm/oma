from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


def test_v12_11_case_variant_forbidden_path_currently_allows_lexically():
    policy = ScopePolicy("scope:v1", allowed_paths=("SRC",), forbidden_paths=("src/secret",))
    transition = FileTransition("SRC/SECRET/file.txt", "before", "after")
    assert evaluate_scope(policy, (transition,)).decision is ScopeDecision.ALLOW
