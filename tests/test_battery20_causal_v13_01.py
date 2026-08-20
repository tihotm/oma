from oma.policy import policy_object_root
from oma.trust import TrustRoot, TrustRootStatus


def test_v13_01_enum_and_string_trust_status_have_same_policy_root():
    left = TrustRoot("root", 1, TrustRootStatus.COMPROMISED, None, 0, None, 1)
    right = TrustRoot("root", 1, "COMPROMISED", None, 0, None, 1)
    assert left != right
    assert policy_object_root("trust-root", left) == policy_object_root("trust-root", right)
