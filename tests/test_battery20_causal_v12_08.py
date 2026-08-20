from oma.identity import TypedIdentity, identity_digest


def test_v12_08_identity_digest_currently_hashes_empty_namespace():
    assert identity_digest(TypedIdentity("", "id:1"))
