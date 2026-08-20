from oma.identity import IdentityDecision, IdentityPolicy, make_typed_identity


def test_v12_07_canonical_identity_constructor_blocks_nul():
    result = make_typed_identity("a", "b\0c", IdentityPolicy("identity:v1"))
    assert result.decision is IdentityDecision.BLOCK
