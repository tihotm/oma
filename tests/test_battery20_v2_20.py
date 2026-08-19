from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_20_integer_and_integral_float_are_both_accepted_with_distinct_types():
    schema = StrictSchema("s", 1, frozenset({"x"}))
    integer = strict_parse_json('{"x":1}', schema)
    floating = strict_parse_json('{"x":1.0}', schema)
    assert integer.decision is IdentityDecision.ALLOW
    assert floating.decision is IdentityDecision.ALLOW
    assert type(integer.value["x"]) is int
    assert type(floating.value["x"]) is float
