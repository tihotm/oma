from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_14_overflowing_json_exponent_blocks():
    result = strict_parse_json('{"value":1e309}', StrictSchema("s", 1, frozenset({"value"})))
    assert result.decision is IdentityDecision.BLOCK
