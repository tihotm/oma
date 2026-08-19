from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_17_trailing_json_data_is_blocked():
    schema = StrictSchema("s", 1, frozenset({"x"}))
    result = strict_parse_json('{"x":1} garbage', schema)
    assert result.decision is IdentityDecision.BLOCK
