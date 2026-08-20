from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle


def test_v11_06_bool_bundle_epoch_currently_accepts():
    binding = PolicyBinding("scope", "scope:v1", "root:1")
    expected = PolicyBundle("bundle:1", True, (binding,))
    presented = PolicyBundle("bundle:1", True, (binding,))
    result = evaluate_policy_bundle(expected, presented, required_policy_kinds=frozenset({"scope"}))
    assert result.decision is PolicyBundleDecision.ALLOW
