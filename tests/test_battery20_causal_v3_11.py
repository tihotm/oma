from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle


def test_11_duplicate_policy_kind_blocks():
    expected = PolicyBundle("bundle", 1, (PolicyBinding("scope", "s", "r1"),))
    presented = PolicyBundle("bundle", 1, (PolicyBinding("scope", "s", "r1"), PolicyBinding("scope", "s2", "r2")))
    result = evaluate_policy_bundle(expected, presented, required_policy_kinds=frozenset({"scope"}))
    assert result.decision is PolicyBundleDecision.BLOCK
    assert "invalid_or_duplicate_presented_policy_kind" in result.reasons
