from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust


def test_selected_compromised_root_blocks_even_precompromise_artifact():
    ctx = TrustContext("ctx", 1, 1, 1, 1, TemporalHighWater(1, 1, 1, 1))
    root = TrustRoot("r", 1, TrustRootStatus.COMPROMISED, activated_epoch=0, compromised_epoch=1)
    artifact = SignedArtifact("a", "r", 1, 1, 1, 1, 0, 10)
    assert evaluate_trust(ctx, (root,), artifact).decision is TrustDecision.BLOCK
