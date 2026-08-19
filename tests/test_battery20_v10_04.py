from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_same_field_can_be_both_required_and_optional():
    schema=StrictSchema("schema",1,frozenset({"a"}),frozenset({"a"}))
    assert strict_parse_json('{"a":1}',schema).decision is IdentityDecision.ALLOW
