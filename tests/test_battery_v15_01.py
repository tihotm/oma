from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


def test_scope_path_text_allows_symlink_escape(tmp_path):
    src=tmp_path/'src'; secret=tmp_path/'secret'; src.mkdir(); secret.mkdir()
    (secret/'data.txt').write_text('secret')
    (src/'link').symlink_to(secret, target_is_directory=True)
    policy=ScopePolicy('scope',('src',),forbidden_paths=('secret',))
    result=evaluate_scope(policy,(FileTransition('src/link/data.txt','a','b'),))
    assert result.decision is ScopeDecision.ALLOW
