from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_13_fractional_json_number_blocks():
    result = strict_parse_json('{"value":1.5}', StrictSchema("s", 1, frozenset({"value"})))
    assert result.decision is IdentityDecision.BLOCK
