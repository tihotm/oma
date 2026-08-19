from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle


def test_12_policy_root_substitution_blocks():
    expected = PolicyBundle("bundle", 1, (PolicyBinding("scope", "scope-v1", "root-a"),))
    presented = PolicyBundle("bundle", 1, (PolicyBinding("scope", "scope-v1", "root-b"),))
    result = evaluate_policy_bundle(expected, presented, required_policy_kinds=frozenset({"scope"}))
    assert result.decision is PolicyBundleDecision.BLOCK
    assert "policy_root_mismatch:scope" in result.reasons
