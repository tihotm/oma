from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust


def test_child_root_must_advance_trust_epoch():
    ctx = TrustContext("ctx", 1, 1, 1, 1, TemporalHighWater(1, 1, 1, 1))
    parent = TrustRoot("p", 1, TrustRootStatus.ACTIVE, activated_epoch=0)
    child = TrustRoot("c", 1, TrustRootStatus.ACTIVE, parent_root_id="p", activated_epoch=1)
    artifact = SignedArtifact("a", "c", 1, 1, 1, 1, 1, 10)
    assert evaluate_trust(ctx, (parent, child), artifact).decision is TrustDecision.BLOCK
