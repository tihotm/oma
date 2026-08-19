from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust


def test_unknown_root_is_blocked():
    context=TrustContext("time",1,1,1,1,TemporalHighWater(1,1,1,1))
    root=TrustRoot("root",1,TrustRootStatus.ACTIVE,activated_epoch=0)
    artifact=SignedArtifact("a","other",1,1,1,1,0,10)
    assert evaluate_trust(context,(root,),artifact).decision is TrustDecision.BLOCK
