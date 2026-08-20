from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


def test_v12_14_ntfs_ads_alias_of_forbidden_file_currently_allows():
    policy = ScopePolicy("scope:v1", allowed_paths=("src",), forbidden_paths=("src/secret",))
    transition = FileTransition("src/secret:stream", "before", "after")
    assert evaluate_scope(policy, (transition,)).decision is ScopeDecision.ALLOW
