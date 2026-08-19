from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustDecision, TrustRoot, evaluate_trust


def test_string_retired_status_is_treated_like_active_root():
    context=TrustContext("time",1,1,5,1,TemporalHighWater(1,1,5,1))
    root=TrustRoot("root",1,"RETIRED",activated_epoch=0,retired_epoch=2)
    artifact=SignedArtifact("a","root",1,1,5,1,3,10)
    assert evaluate_trust(context,(root,),artifact).decision is TrustDecision.ALLOW
