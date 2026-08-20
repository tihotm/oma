from oma.policy import policy_object_root
from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope


def test_v13_11_root_equivalent_scope_container_types_both_execute():
    left = ScopePolicy("scope:v1", ("src",))
    right = ScopePolicy("scope:v1", ["src"])
    transition = FileTransition("src/a.txt", "before", "after")
    assert policy_object_root("scope", left) == policy_object_root("scope", right)
    assert evaluate_scope(left, (transition,)).decision is ScopeDecision.ALLOW
    assert evaluate_scope(right, (transition,)).decision is ScopeDecision.ALLOW
