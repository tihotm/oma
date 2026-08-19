from oma.identity import IdentityDecision, IdentityPolicy, make_typed_identity


def test_numeric_identity_policy_id_is_accepted():
    assert make_typed_identity("ns","id",IdentityPolicy(1)).decision is IdentityDecision.ALLOW
