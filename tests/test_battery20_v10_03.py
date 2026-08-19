from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_newline_required_field_name_is_accepted():
    schema=StrictSchema("schema",1,frozenset({"a\n1"}))
    assert strict_parse_json('{"a\\n1":1}',schema).decision is IdentityDecision.ALLOW
