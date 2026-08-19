from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust


def test_missing_parent_root_blocks_selected_lineage():
    ctx = TrustContext("ctx", 2, 1, 2, 1, TemporalHighWater(2, 1, 2, 1))
    child = TrustRoot("c", 2, TrustRootStatus.ACTIVE, parent_root_id="missing", activated_epoch=1)
    artifact = SignedArtifact("a", "c", 2, 1, 2, 1, 2, 10)
    assert evaluate_trust(ctx, (child,), artifact).decision is TrustDecision.BLOCK
