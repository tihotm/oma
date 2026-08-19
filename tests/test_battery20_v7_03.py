from dataclasses import replace
from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustRoot, TrustRootStatus
from oma.trust_registry import SQLiteTrustArtifactRegistry, TrustRegistryDecision


def test_same_artifact_id_changed_payload_conflicts(tmp_path):
    r=SQLiteTrustArtifactRegistry(tmp_path/"oma.db")
    c=TrustContext("time:1",1,1,1,1,TemporalHighWater(1,1,1,1))
    roots=(TrustRoot("root",1,TrustRootStatus.ACTIVE,activated_epoch=0),)
    a=SignedArtifact("a","root",1,1,1,1,0,10)
    assert r.register(c,roots,a).decision is TrustRegistryDecision.WRITTEN
    assert r.register(c,roots,replace(a,expires_epoch=9)).decision is TrustRegistryDecision.CONFLICT
