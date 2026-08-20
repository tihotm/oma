from oma.policy import policy_object_root
from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust


def ctx():
    return TrustContext("time:1", 1, 1, 1, 1, TemporalHighWater(1, 1, 1, 1))

def art():
    return SignedArtifact("artifact:1", "root", 1, 1, 1, 1, 1, 10)


def test_v13_08_missing_compromise_boundary_is_bypassed_by_string_status_with_same_root():
    enum_root = TrustRoot("root", 1, TrustRootStatus.COMPROMISED, None, 0, None, None)
    string_root = TrustRoot("root", 1, "COMPROMISED", None, 0, None, None)
    assert policy_object_root("trust-root", enum_root) == policy_object_root("trust-root", string_root)
    assert evaluate_trust(ctx(), (enum_root,), art()).decision is TrustDecision.BLOCK
    assert evaluate_trust(ctx(), (string_root,), art()).decision is TrustDecision.ALLOW
