from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle


def test_v11_09_numeric_bundle_identity_currently_accepts_when_bound_equal():
    binding = PolicyBinding("scope", "scope:v1", "root:1")
    expected = PolicyBundle(1, 1, (binding,))
    presented = PolicyBundle(1, 1, (binding,))
    result = evaluate_policy_bundle(
        expected,
        presented,
        required_policy_kinds=frozenset({"scope"}),
        bound_policy_bundle_ids=(1,),
    )
    assert result.decision is PolicyBundleDecision.ALLOW
