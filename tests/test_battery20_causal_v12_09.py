from oma.identity import TypedIdentity, identity_digest


def test_v12_09_numeric_and_string_identity_fields_collide_under_fstring():
    left = TypedIdentity(1, "id:1")
    right = TypedIdentity("1", "id:1")
    assert left != right
    assert identity_digest(left) == identity_digest(right)
