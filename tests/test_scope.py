import pytest

from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


@pytest.fixture
def policy() -> ScopePolicy:
    return ScopePolicy(
        scope_policy_id="scope-v1",
        allowed_paths=("src", "tests"),
        forbidden_paths=("src/secrets",),
        protected_roles=frozenset({"VERIFIER", "HIDDEN_TEST", "POLICY"}),
        review_roles=frozenset({"CI", "TOOLCHAIN"}),
    )


def transition(path: str = "src/app.py", **changes) -> FileTransition:
    values = {
        "path": path,
        "before_digest": "before",
        "after_digest": "after",
        "roles": frozenset(),
        "touched": True,
    }
    values.update(changes)
    return FileTransition(**values)


def test_legitimate_change_is_allowed(policy):
    assert evaluate_scope(policy, [transition()]).decision is ScopeDecision.ALLOW


def test_scope_expansion_is_blocked(policy):
    result = evaluate_scope(policy, [transition("docs/readme.md")])
    assert result.decision is ScopeDecision.BLOCK
    assert result.reasons == ("scope_expansion:docs/readme.md",)


def test_forbidden_path_is_blocked(policy):
    result = evaluate_scope(policy, [transition("src/secrets/key.txt")])
    assert result.decision is ScopeDecision.BLOCK


@pytest.mark.parametrize("role", ["VERIFIER", "HIDDEN_TEST", "POLICY"])
def test_protected_semantic_roles_are_blocked(policy, role):
    result = evaluate_scope(
        policy,
        [transition("tests/check.py", roles=frozenset({role}))],
    )
    assert result.decision is ScopeDecision.BLOCK


def test_protected_touch_and_restore_is_still_blocked(policy):
    result = evaluate_scope(
        policy,
        [
            transition(
                "tests/verifier.py",
                before_digest="same",
                after_digest="same",
                roles=frozenset({"VERIFIER"}),
            )
        ],
    )
    assert result.decision is ScopeDecision.BLOCK


@pytest.mark.parametrize("role", ["CI", "TOOLCHAIN"])
def test_sensitive_role_requires_review(policy, role):
    result = evaluate_scope(
        policy,
        [transition("tests/support.py", roles=frozenset({role}))],
    )
    assert result.decision is ScopeDecision.REVIEW


def test_review_touch_and_restore_still_requires_review(policy):
    result = evaluate_scope(
        policy,
        [
            transition(
                "tests/support.py",
                before_digest="same",
                after_digest="same",
                roles=frozenset({"CI"}),
            )
        ],
    )
    assert result.decision is ScopeDecision.REVIEW


def test_changed_state_without_touch_history_is_blocked(policy):
    result = evaluate_scope(policy, [transition(touched=False)])
    assert result.decision is ScopeDecision.BLOCK
    assert result.reasons == ("transition_history_inconsistent:src/app.py",)


def test_untouched_unchanged_entry_is_ignored(policy):
    result = evaluate_scope(
        policy,
        [transition(before_digest="same", after_digest="same", touched=False)],
    )
    assert result.decision is ScopeDecision.ALLOW


@pytest.mark.parametrize("path", ["../src/app.py", "/src/app.py", "src/../../etc/passwd"])
def test_unsafe_paths_fail_closed(policy, path):
    assert evaluate_scope(policy, [transition(path)]).decision is ScopeDecision.BLOCK


def test_windows_separator_is_normalized(policy):
    result = evaluate_scope(policy, [transition(r"src\feature\app.py")])
    assert result.decision is ScopeDecision.ALLOW


def test_empty_allowed_scope_fails_closed():
    policy = ScopePolicy(scope_policy_id="scope-v1", allowed_paths=())
    assert evaluate_scope(policy, []).decision is ScopeDecision.BLOCK


def test_missing_policy_identity_fails_closed():
    policy = ScopePolicy(scope_policy_id="", allowed_paths=("src",))
    assert evaluate_scope(policy, []).decision is ScopeDecision.BLOCK


def test_block_precedes_review(policy):
    result = evaluate_scope(
        policy,
        [
            transition("tests/support.py", roles=frozenset({"CI"})),
            transition("docs/outside.py"),
        ],
    )
    assert result.decision is ScopeDecision.BLOCK
