from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust


def test_v13_10_unknown_trust_root_still_blocks():
    context = TrustContext("time:1", 1, 1, 1, 1, TemporalHighWater(1, 1, 1, 1))
    root = TrustRoot("root", 1, TrustRootStatus.ACTIVE, None, 0, None, None)
    artifact = SignedArtifact("artifact:1", "other", 1, 1, 1, 1, 1, 10)
    assert evaluate_trust(context, (root,), artifact).decision is TrustDecision.BLOCK
