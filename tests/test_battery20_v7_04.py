from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustRoot, TrustRootStatus
from oma.trust_registry import SQLiteTrustArtifactRegistry, TrustRegistryDecision


def test_lookup_rejects_different_temporal_context_id(tmp_path):
    r=SQLiteTrustArtifactRegistry(tmp_path/"oma.db")
    c=TrustContext("time:1",1,1,1,1,TemporalHighWater(1,1,1,1))
    roots=(TrustRoot("root",1,TrustRootStatus.ACTIVE,activated_epoch=0),)
    a=SignedArtifact("a","root",1,1,1,1,0,10)
    assert r.register(c,roots,a).decision is TrustRegistryDecision.WRITTEN
    other=TrustContext("time:2",1,1,1,1,TemporalHighWater(1,1,1,1))
    assert r.get(other,roots,"a") is None
