from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_18_non_finite_json_number_is_blocked():
    schema = StrictSchema("s", 1, frozenset({"x"}))
    result = strict_parse_json('{"x":NaN}', schema)
    assert result.decision is IdentityDecision.BLOCK
