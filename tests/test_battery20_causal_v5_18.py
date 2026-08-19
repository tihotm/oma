from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust


def test_active_child_of_compromised_parent_currently_allows():
    ctx = TrustContext("ctx", 2, 1, 2, 1, TemporalHighWater(2, 1, 2, 1))
    parent = TrustRoot("p", 1, TrustRootStatus.COMPROMISED, activated_epoch=0, compromised_epoch=1)
    child = TrustRoot("c", 2, TrustRootStatus.ACTIVE, parent_root_id="p", activated_epoch=2)
    artifact = SignedArtifact("a", "c", 2, 1, 2, 1, 2, 10)
    assert evaluate_trust(ctx, (parent, child), artifact).decision is TrustDecision.ALLOW
