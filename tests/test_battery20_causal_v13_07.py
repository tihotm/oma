from oma.policy import policy_object_root
from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust


def ctx():
    return TrustContext("time:1", 1, 1, 1, 1, TemporalHighWater(1, 1, 1, 1))

def art():
    return SignedArtifact("artifact:1", "root", 1, 1, 1, 1, 1, 10)


def test_v13_07_policy_root_equivalent_retired_string_bypasses_stale_status():
    enum_root = TrustRoot("root", 1, TrustRootStatus.RETIRED, None, 0, 2, None)
    string_root = TrustRoot("root", 1, "RETIRED", None, 0, 2, None)
    assert policy_object_root("trust-root", enum_root) == policy_object_root("trust-root", string_root)
    assert evaluate_trust(ctx(), (enum_root,), art()).decision is TrustDecision.STALE
    assert evaluate_trust(ctx(), (string_root,), art()).decision is TrustDecision.ALLOW
