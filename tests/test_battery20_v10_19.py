from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, TrustRootStatus, evaluate_trust


def test_numeric_root_identity_is_accepted():
    context=TrustContext("time",1,1,1,1,TemporalHighWater(1,1,1,1))
    root=TrustRoot(1,1,TrustRootStatus.ACTIVE,activated_epoch=0)
    artifact=SignedArtifact("a",1,1,1,1,1,0,10)
    assert evaluate_trust(context,(root,),artifact).decision is TrustDecision.ALLOW
