from oma.trust import SignedArtifact, TemporalHighWater, TrustContext, TrustRoot, TrustRootStatus
from oma.trust_registry import SQLiteTrustArtifactRegistry, TrustRegistryDecision


def ctx(epoch):
    return TrustContext("time:1", epoch, epoch, epoch, epoch, TemporalHighWater(epoch, epoch, epoch, epoch))

def root(epoch):
    return (TrustRoot("root", epoch, TrustRootStatus.ACTIVE, activated_epoch=0),)

def art(name, epoch):
    return SignedArtifact(name, "root", epoch, epoch, epoch, epoch, 0, 10)

def test_registry_accepts_lower_epoch_after_higher_epoch_was_persisted(tmp_path):
    r = SQLiteTrustArtifactRegistry(tmp_path / "oma.db")
    assert r.register(ctx(2), root(2), art("a2", 2)).decision is TrustRegistryDecision.WRITTEN
    assert r.register(ctx(1), root(1), art("a1", 1)).decision is TrustRegistryDecision.WRITTEN
