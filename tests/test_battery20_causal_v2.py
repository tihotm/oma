from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


def _scope_policy():
    return ScopePolicy(
        scope_policy_id="scope-v2",
        allowed_paths=("src",),
        forbidden_paths=("src/secret",),
        protected_roles=frozenset({"protected"}),
        review_roles=frozenset({"review"}),
    )


def test_01_changed_transition_cannot_claim_untouched():
    result = evaluate_scope(_scope_policy(), (FileTransition("src/a.py", "before", "after", touched=False),))
    assert result.decision is ScopeDecision.BLOCK


def test_02_hidden_touch_restore_is_accepted_when_caller_sets_untouched():
    result = evaluate_scope(_scope_policy(), (FileTransition("src/a.py", "same", "same", roles=frozenset({"protected"}), touched=False),))
    assert result.decision is ScopeDecision.ALLOW


def test_03_omitted_protected_role_allows_changed_file():
    result = evaluate_scope(_scope_policy(), (FileTransition("src/a.py", "before", "after", roles=frozenset(), touched=True),))
    assert result.decision is ScopeDecision.ALLOW
