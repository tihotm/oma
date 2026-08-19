from oma.identity import IdentityDecision, IdentityPolicy, make_typed_identity


def test_14_mixed_script_namespace_spoof_is_accepted_as_distinct():
    policy = IdentityPolicy("id-v2")
    latin = make_typed_identity("repo", "x", policy)
    spoof = make_typed_identity("repо", "x", policy)  # final o is Cyrillic
    assert latin.decision is IdentityDecision.ALLOW
    assert spoof.decision is IdentityDecision.ALLOW
    assert latin.identity != spoof.identity
