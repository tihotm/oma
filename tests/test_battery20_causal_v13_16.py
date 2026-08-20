from oma.policy import PolicyBinding, PolicyBundle, PolicyBundleDecision, evaluate_policy_bundle, policy_object_root
from oma.trust import TrustRoot, TrustRootStatus


def test_v13_16_policy_bundle_accepts_type_erased_compromised_trust_binding():
    enum_root = TrustRoot("root", 1, TrustRootStatus.COMPROMISED, None, 0, None, 1)
    string_root = TrustRoot("root", 1, "COMPROMISED", None, 0, None, 1)
    expected = PolicyBundle("bundle:1", 1, (PolicyBinding("trust", "trust:v1", policy_object_root("trust-root", enum_root)),))
    presented = PolicyBundle("bundle:1", 1, (PolicyBinding("trust", "trust:v1", policy_object_root("trust-root", string_root)),))
    result = evaluate_policy_bundle(expected, presented, required_policy_kinds=frozenset({"trust"}))
    assert enum_root != string_root
    assert result.decision is PolicyBundleDecision.ALLOW
