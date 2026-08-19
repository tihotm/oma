from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_16_duplicate_json_fields_are_blocked():
    schema = StrictSchema("s", 1, frozenset({"x"}))
    result = strict_parse_json('{"x":1,"x":2}', schema)
    assert result.decision is IdentityDecision.BLOCK
