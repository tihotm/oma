from oma.identity import IdentityDecision, StrictSchema, strict_parse_json


def test_11_lone_surrogate_string_is_currently_accepted():
    result = strict_parse_json('{"value":"\\ud800"}', StrictSchema("s", 1, frozenset({"value"})))
    assert result.decision is IdentityDecision.ALLOW
    assert result.value is not None and result.value["value"] == "\ud800"
