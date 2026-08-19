from oma.identity import IdentityPolicy, make_typed_identity


def test_13_compatibility_unicode_canonicalizes_to_same_identity():
    policy = IdentityPolicy("id-v2")
    a = make_typed_identity("ＲＥＰＯ", "ＡＢＣ", policy)
    b = make_typed_identity("repo", "abc", policy)
    assert a.identity == b.identity
