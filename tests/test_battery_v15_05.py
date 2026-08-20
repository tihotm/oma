from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


def test_scope_normal_allowed_path_allows():
    policy=ScopePolicy('scope',('src',),forbidden_paths=('outside',))
    result=evaluate_scope(policy,(FileTransition('src/file.txt','a','b'),))
    assert result.decision is ScopeDecision.ALLOW
