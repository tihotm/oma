from oma.policy import policy_object_root
from oma.trust import TrustRoot, TrustRootStatus


def test_v13_05_distinct_semantic_trust_status_changes_policy_root():
    active = TrustRoot("root", 1, TrustRootStatus.ACTIVE, None, 0, None, None)
    compromised = TrustRoot("root", 1, TrustRootStatus.COMPROMISED, None, 0, None, 1)
    assert policy_object_root("trust-root", active) != policy_object_root("trust-root", compromised)
