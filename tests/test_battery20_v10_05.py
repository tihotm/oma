from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_unknown_field_is_blocked():
    schema=StrictSchema("schema",1,frozenset())
    assert strict_parse_json('{"x":1}',schema).decision is IdentityDecision.BLOCK
