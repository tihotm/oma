from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust


def test_artifact_issued_in_future_blocks():
    ctx = TrustContext("ctx", 1, 1, 5, 1, TemporalHighWater(1, 1, 5, 1))
    root = TrustRoot("r", 1, TrustRootStatus.ACTIVE, activated_epoch=0)
    artifact = SignedArtifact("a", "r", 1, 1, 5, 1, 6, 10)
    assert evaluate_trust(ctx, (root,), artifact).decision is TrustDecision.BLOCK
