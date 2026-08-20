from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle, policy_object_root
from oma.scope import ScopePolicy


def test_v13_18_policy_bundle_accepts_type_erased_scope_binding():
    left = ScopePolicy("scope:v1", ("src",))
    right = ScopePolicy("scope:v1", ["src"])
    expected = PolicyBundle("bundle:1", 1, (PolicyBinding("scope", "scope:v1", policy_object_root("scope", left)),))
    presented = PolicyBundle("bundle:1", 1, (PolicyBinding("scope", "scope:v1", policy_object_root("scope", right)),))
    assert left != right
    assert evaluate_policy_bundle(expected, presented, required_policy_kinds=frozenset({"scope"})).decision is PolicyBundleDecision.ALLOW
