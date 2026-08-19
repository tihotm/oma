from oma.identity import IdentityDecision, IdentityPolicy, make_typed_identity


def test_integer_one_is_accepted_as_case_sensitive_flag():
    result=make_typed_identity("NS","ABC",IdentityPolicy("id",case_sensitive=1))
    assert result.decision is IdentityDecision.ALLOW
    assert result.identity.canonical_id == "ABC"
