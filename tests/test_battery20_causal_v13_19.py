from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle, policy_object_root
from oma.trust import TrustRoot, TrustRootStatus


def test_v13_19_semantically_different_trust_status_root_still_blocks_bundle():
    active = TrustRoot("root", 1, TrustRootStatus.ACTIVE, None, 0, None, None)
    compromised = TrustRoot("root", 1, TrustRootStatus.COMPROMISED, None, 0, None, 1)
    expected = PolicyBundle("bundle:1", 1, (PolicyBinding("trust", "trust:v1", policy_object_root("trust-root", active)),))
    presented = PolicyBundle("bundle:1", 1, (PolicyBinding("trust", "trust:v1", policy_object_root("trust-root", compromised)),))
    assert evaluate_policy_bundle(expected, presented, required_policy_kinds=frozenset({"trust"})).decision is PolicyBundleDecision.BLOCK
