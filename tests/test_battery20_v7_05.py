from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustRoot, TrustRootStatus
from oma.trust_registry import SQLiteTrustArtifactRegistry, TrustRegistryDecision


def test_carriage_return_artifact_id_is_accepted(tmp_path):
    r=SQLiteTrustArtifactRegistry(tmp_path/"oma.db")
    c=TrustContext("time:1",1,1,1,1,TemporalHighWater(1,1,1,1))
    roots=(TrustRoot("root",1,TrustRootStatus.ACTIVE,activated_epoch=0),)
    a=SignedArtifact("a\rb","root",1,1,1,1,0,10)
    assert r.register(c,roots,a).decision is TrustRegistryDecision.WRITTEN
