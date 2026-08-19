from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle


def test_13_bound_policy_bundle_id_mismatch_blocks():
    bundle = PolicyBundle("bundle", 1, (PolicyBinding("scope", "scope-v1", "root-a"),))
    result = evaluate_policy_bundle(
        bundle,
        bundle,
        required_policy_kinds=frozenset({"scope"}),
        bound_policy_bundle_ids=("other-bundle",),
    )
    assert result.decision is PolicyBundleDecision.BLOCK
    assert "policy_bundle_binding_mismatch" in result.reasons
