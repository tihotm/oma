from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle


def test_v11_10_policy_root_mismatch_still_blocks():
    expected = PolicyBundle("bundle:1", 1, (PolicyBinding("scope", "scope:v1", "root:1"),))
    presented = PolicyBundle("bundle:1", 1, (PolicyBinding("scope", "scope:v1", "root:2"),))
    result = evaluate_policy_bundle(expected, presented, required_policy_kinds=frozenset({"scope"}))
    assert result.decision is PolicyBundleDecision.BLOCK
