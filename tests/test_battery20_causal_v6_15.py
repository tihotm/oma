from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_15_bom_prefixed_json_blocks():
    result = strict_parse_json('\ufeff{"value":1}', StrictSchema("s", 1, frozenset({"value"})))
    assert result.decision is IdentityDecision.BLOCK
