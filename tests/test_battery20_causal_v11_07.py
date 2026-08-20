from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle


def test_v11_07_control_character_policy_kind_currently_accepts():
    kind = "scope\nshadow"
    binding = PolicyBinding(kind, "scope:v1", "root:1")
    expected = PolicyBundle("bundle:1", 1, (binding,))
    presented = PolicyBundle("bundle:1", 1, (binding,))
    result = evaluate_policy_bundle(expected, presented, required_policy_kinds=frozenset({kind}))
    assert result.decision is PolicyBundleDecision.ALLOW
