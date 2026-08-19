from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_12_escaped_duplicate_json_key_blocks():
    result = strict_parse_json('{"a":1,"\\u0061":2}', StrictSchema("s", 1, frozenset({"a"})))
    assert result.decision is IdentityDecision.BLOCK
