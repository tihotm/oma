from oma.identity import IdentityDecision, IdentityPolicy, make_typed_identity


def test_string_false_is_treated_as_case_sensitive_truth():
    result=make_typed_identity("NS","ABC",IdentityPolicy("id",case_sensitive="false"))
    assert result.decision is IdentityDecision.ALLOW
    assert result.identity.canonical_id == "ABC"
