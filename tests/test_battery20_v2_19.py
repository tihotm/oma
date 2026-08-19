from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_19_integer_beyond_safe_json_range_is_blocked():
    schema = StrictSchema("s", 1, frozenset({"x"}))
    result = strict_parse_json('{"x":9007199254740992}', schema)
    assert result.decision is IdentityDecision.BLOCK
