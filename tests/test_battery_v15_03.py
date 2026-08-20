from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


def test_scope_path_text_allows_hardlink_to_external_object(tmp_path):
    src=tmp_path/'src'; outside=tmp_path/'outside'; src.mkdir(); outside.mkdir()
    target=outside/'secret.txt'; target.write_text('secret')
    alias=src/'alias.txt'; alias.hardlink_to(target)
    policy=ScopePolicy('scope',('src',),forbidden_paths=('outside',))
    assert evaluate_scope(policy,(FileTransition('src/alias.txt','a','b'),)).decision is ScopeDecision.ALLOW
