from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_boolean_schema_version_is_accepted():
    schema=StrictSchema("schema",True,frozenset())
    assert strict_parse_json("{}",schema).decision is IdentityDecision.ALLOW
