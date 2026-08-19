from oma.trust import (
    SignedArtifact,
    TemporalHighWater,
    TrustContext,
    TrustRoot,
    TrustRootStatus,
)
from oma.trust_registry import SQLiteTrustArtifactRegistry, TrustRegistryDecision


def _ctx(context_id="ctx", epoch=1):
    return TrustContext(
        temporal_context_id=context_id,
        current_trust_epoch=epoch,
        current_authority_epoch=epoch,
        current_logical_epoch=epoch,
        current_state_version=epoch,
        high_water=TemporalHighWater(epoch, epoch, epoch, epoch),
    )


def _roots(epoch=1):
    return (
        TrustRoot(
            root_id="root-1",
            trust_epoch=epoch,
            status=TrustRootStatus.ACTIVE,
            activated_epoch=0,
        ),
    )


def _artifact(artifact_id="artifact-1", epoch=1):
    return SignedArtifact(
        artifact_id=artifact_id,
        issuer_root_id="root-1",
        trust_epoch=epoch,
        authority_epoch=epoch,
        logical_epoch=epoch,
        state_version=epoch,
        issued_epoch=epoch,
        expires_epoch=epoch + 10,
    )


def test_01_unregistered_trust_artifact_is_not_authoritative(tmp_path):
    registry = SQLiteTrustArtifactRegistry(tmp_path / "oma.db")
    assert registry.get(_ctx(), _roots(), "artifact-1") is None


def test_02_registered_artifact_cannot_cross_temporal_context(tmp_path):
    registry = SQLiteTrustArtifactRegistry(tmp_path / "oma.db")
    assert registry.register(_ctx(), _roots(), _artifact()).decision is TrustRegistryDecision.WRITTEN
    assert registry.get(_ctx("ctx-other"), _roots(), "artifact-1") is None
