from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustRoot, TrustRootStatus
from oma.trust_registry import SQLiteTrustArtifactRegistry, TrustRegistryDecision


def test_same_temporal_context_accepts_divergent_root_sets(tmp_path):
    r = SQLiteTrustArtifactRegistry(tmp_path / "oma.db")
    c = TrustContext("time:1", 1, 1, 1, 1, TemporalHighWater(1,1,1,1))
    roots_a = (TrustRoot("root-a",1,TrustRootStatus.ACTIVE,activated_epoch=0),)
    roots_b = (TrustRoot("root-b",1,TrustRootStatus.ACTIVE,activated_epoch=0),)
    a = SignedArtifact("a","root-a",1,1,1,1,0,10)
    b = SignedArtifact("b","root-b",1,1,1,1,0,10)
    assert r.register(c, roots_a, a).decision is TrustRegistryDecision.WRITTEN
    assert r.register(c, roots_b, b).decision is TrustRegistryDecision.WRITTEN
