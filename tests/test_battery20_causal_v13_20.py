from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle


def test_v13_20_required_policy_kind_set_mismatch_still_blocks():
    binding = PolicyBinding("scope", "scope:v1", "root:1")
    bundle = PolicyBundle("bundle:1", 1, (binding,))
    result = evaluate_policy_bundle(bundle, bundle, required_policy_kinds=frozenset({"scope", "trust"}))
    assert result.decision is PolicyBundleDecision.BLOCK
