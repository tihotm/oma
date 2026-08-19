from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_numeric_schema_id_is_accepted():
    schema=StrictSchema(1,1,frozenset())
    assert strict_parse_json("{}",schema).decision is IdentityDecision.ALLOW
