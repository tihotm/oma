from dataclasses import replace

from oma.identity import IdentityDecision, IdentityPolicy, identity_digest, make_typed_identity
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


def test_03_registered_artifact_cannot_cross_root_set(tmp_path):
    registry = SQLiteTrustArtifactRegistry(tmp_path / "oma.db")
    roots = _roots()
    assert registry.register(_ctx(), roots, _artifact()).decision is TrustRegistryDecision.WRITTEN
    mutated_roots = (replace(roots[0], activated_epoch=1),)
    assert registry.get(_ctx(), mutated_roots, "artifact-1") is None


def test_04_same_artifact_id_cannot_be_registered_twice(tmp_path):
    registry = SQLiteTrustArtifactRegistry(tmp_path / "oma.db")
    first = registry.register(_ctx(), _roots(), _artifact())
    second = registry.register(_ctx(), _roots(), replace(_artifact(), expires_epoch=99))
    assert first.decision is TrustRegistryDecision.WRITTEN
    assert second.decision is TrustRegistryDecision.CONFLICT


def test_05_temporal_high_water_is_not_durable_registry_state(tmp_path):
    path = tmp_path / "oma.db"
    registry = SQLiteTrustArtifactRegistry(path)
    artifact = _artifact()
    assert registry.register(_ctx(), _roots(), artifact).decision is TrustRegistryDecision.WRITTEN
    reopened = SQLiteTrustArtifactRegistry(path)
    assert reopened.get(_ctx(), _roots(), artifact.artifact_id) == artifact


def test_06_case_aliases_collapse_to_one_identity():
    policy = IdentityPolicy("id-policy")
    a = make_typed_identity("Subject", "Straße", policy)
    b = make_typed_identity("subject", "STRASSE", policy)
    assert a.decision is IdentityDecision.ALLOW
    assert b.decision is IdentityDecision.ALLOW
    assert a.identity == b.identity
