from oma.identity import TypedIdentity, content_digest, identity_digest


def test_v12_10_content_and_identity_digest_domains_are_separated():
    identity = TypedIdentity("a", "b")
    assert identity_digest(identity) != content_digest(b"a\0b")
