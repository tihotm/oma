from oma.identity import TypedIdentity, identity_digest


def test_v12_06_identity_digest_delimiter_collision_is_observed():
    left = TypedIdentity("a", "b\0c")
    right = TypedIdentity("a\0b", "c")
    assert left != right
    assert identity_digest(left) == identity_digest(right)
