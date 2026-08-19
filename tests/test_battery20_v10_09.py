from oma.identity import IdentityDecision, IdentityPolicy, make_typed_identity


def test_format_control_character_is_blocked():
    assert make_typed_identity("ns","a\u200db",IdentityPolicy("id")).decision is IdentityDecision.BLOCK
