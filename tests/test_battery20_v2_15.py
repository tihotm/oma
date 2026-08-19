from oma.identity import IdentityPolicy, identity_digest, make_typed_identity


def test_15_namespace_and_id_framing_prevents_delimiter_confusion():
    policy = IdentityPolicy("id-v2")
    a = make_typed_identity("a:b", "c", policy).identity
    b = make_typed_identity("a", "b:c", policy).identity
    assert a is not None and b is not None
    assert identity_digest(a) != identity_digest(b)
