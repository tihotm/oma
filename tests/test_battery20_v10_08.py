from oma.identity import IdentityDecision, IdentityPolicy, make_typed_identity


def test_unknown_unicode_form_is_blocked():
    assert make_typed_identity("ns","id",IdentityPolicy("id",unicode_form="NFD")).decision is IdentityDecision.BLOCK
