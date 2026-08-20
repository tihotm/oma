from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


def test_scope_traversal_is_blocked():
    policy=ScopePolicy('scope',('src',),forbidden_paths=('outside',))
    result=evaluate_scope(policy,(FileTransition('src/../outside/secret.txt','a','b'),))
    assert result.decision is ScopeDecision.BLOCK
