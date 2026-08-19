from dataclasses import replace

from oma.identity import (
    IdentityDecision,
    IdentityPolicy,
    StrictSchema,
    identity_digest,
    make_typed_identity,
    strict_parse_json,
)
from oma.scope import FileTransition, ScopeDecision, ScopePolicy, evaluate_scope
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


def _schema():
    return StrictSchema("schema", 1, frozenset({"n"}))


def _scope():
    return ScopePolicy(
        "scope-policy",
        allowed_paths=("src",),
        forbidden_paths=("src/secrets",),
        protected_roles=frozenset({"security"}),
        review_roles=frozenset({"config"}),
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


def test_07_nfkc_compatibility_aliases_collapse():
    policy = IdentityPolicy("id-policy")
    a = make_typed_identity("subject", "ＡＢＣ", policy)
    b = make_typed_identity("subject", "ABC", policy)
    assert a.decision is IdentityDecision.ALLOW
    assert b.decision is IdentityDecision.ALLOW
    assert a.identity == b.identity


def test_08_control_character_in_identity_is_blocked():
    result = make_typed_identity("subject", "abc\x00def", IdentityPolicy("id-policy"))
    assert result.decision is IdentityDecision.BLOCK


def test_09_same_id_in_different_namespaces_has_different_digest():
    policy = IdentityPolicy("id-policy")
    a = make_typed_identity("subject", "123", policy)
    b = make_typed_identity("policy", "123", policy)
    assert a.identity is not None and b.identity is not None
    assert identity_digest(a.identity) != identity_digest(b.identity)


def test_10_mixed_script_namespace_spoof_is_currently_accepted():
    policy = IdentityPolicy("id-policy")
    latin = make_typed_identity("subject", "123", policy)
    spoof = make_typed_identity("ѕubject", "123", policy)
    assert latin.decision is IdentityDecision.ALLOW
    assert spoof.decision is IdentityDecision.ALLOW
    assert latin.identity != spoof.identity


def test_11_duplicate_json_fields_are_blocked():
    result = strict_parse_json('{"n":1,"n":2}', _schema())
    assert result.decision is IdentityDecision.BLOCK


def test_12_trailing_json_data_is_blocked():
    result = strict_parse_json('{"n":1} {"n":2}', _schema())
    assert result.decision is IdentityDecision.BLOCK


def test_13_non_finite_json_number_is_blocked():
    result = strict_parse_json('{"n":NaN}', _schema())
    assert result.decision is IdentityDecision.BLOCK


def test_14_integer_outside_exact_interop_range_is_blocked():
    result = strict_parse_json('{"n":9007199254740992}', _schema())
    assert result.decision is IdentityDecision.BLOCK


def test_15_integer_and_integral_float_are_both_accepted_with_different_runtime_types():
    integer = strict_parse_json('{"n":1}', _schema())
    floating = strict_parse_json('{"n":1.0}', _schema())
    assert integer.decision is IdentityDecision.ALLOW
    assert floating.decision is IdentityDecision.ALLOW
    assert integer.value is not None and floating.value is not None
    assert type(integer.value["n"]) is int
    assert type(floating.value["n"]) is float


def test_16_scope_path_traversal_is_blocked():
    result = evaluate_scope(_scope(), (FileTransition("src/../secret", "a", "b"),))
    assert result.decision is ScopeDecision.BLOCK
