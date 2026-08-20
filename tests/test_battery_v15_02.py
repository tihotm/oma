from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


def test_scope_does_not_distinguish_real_directory_from_symlink(tmp_path):
    src=tmp_path/'src'; outside=tmp_path/'outside'; src.mkdir(); outside.mkdir()
    (src/'alias').symlink_to(outside, target_is_directory=True)
    policy=ScopePolicy('scope',('src',),forbidden_paths=('outside',))
    assert evaluate_scope(policy,(FileTransition('src/alias/new.txt',None,'digest'),)).decision is ScopeDecision.ALLOW
