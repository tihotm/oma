from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class TrustDecision(StrEnum):
    ALLOW = "ALLOW"
    STALE = "STALE"
    BLOCK = "BLOCK"


class TrustRootStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    COMPROMISED = "COMPROMISED"


@dataclass(frozen=True, slots=True)
class TrustRoot:
    root_id: str
    trust_epoch: int
    status: TrustRootStatus
    parent_root_id: str | None = None
    activated_epoch: int = 0
    retired_epoch: int | None = None
    compromised_epoch: int | None = None


@dataclass(frozen=True, slots=True)
class TemporalHighWater:
    trust_epoch: int
    authority_epoch: int
    logical_epoch: int
    state_version: int


@dataclass(frozen=True, slots=True)
class SignedArtifact:
    artifact_id: str
    issuer_root_id: str
    trust_epoch: int
    authority_epoch: int
    logical_epoch: int
    state_version: int
    issued_epoch: int
    expires_epoch: int


@dataclass(frozen=True, slots=True)
class TrustContext:
    temporal_context_id: str
    current_trust_epoch: int
    current_authority_epoch: int
    current_logical_epoch: int
    current_state_version: int
    high_water: TemporalHighWater


@dataclass(frozen=True, slots=True)
class TrustResult:
    decision: TrustDecision
    reasons: tuple[str, ...] = ()


def evaluate_trust(
    context: TrustContext,
    roots: Iterable[TrustRoot],
    artifact: SignedArtifact,
) -> TrustResult:
    items = tuple(roots)
    if (
        not context.temporal_context_id
        or min(
            context.current_trust_epoch,
            context.current_authority_epoch,
            context.current_logical_epoch,
            context.current_state_version,
            context.high_water.trust_epoch,
            context.high_water.authority_epoch,
            context.high_water.logical_epoch,
            context.high_water.state_version,
        ) < 0
    ):
        return TrustResult(TrustDecision.BLOCK, ("invalid_temporal_context",))

    current = (
        context.current_trust_epoch,
        context.current_authority_epoch,
        context.current_logical_epoch,
        context.current_state_version,
    )
    high = (
        context.high_water.trust_epoch,
        context.high_water.authority_epoch,
        context.high_water.logical_epoch,
        context.high_water.state_version,
    )
    if any(c < h for c, h in zip(current, high)):
        return TrustResult(TrustDecision.BLOCK, ("temporal_high_water_rollback",))

    ids = [root.root_id for root in items]
    if not all(ids) or len(ids) != len(set(ids)):
        return TrustResult(TrustDecision.BLOCK, ("invalid_or_duplicate_trust_root",))
    by_id = {root.root_id: root for root in items}
    root = by_id.get(artifact.issuer_root_id)
    if root is None:
        return TrustResult(TrustDecision.BLOCK, ("unknown_trust_root",))

    for candidate in items:
        if (
            candidate.trust_epoch < 0
            or candidate.activated_epoch < 0
            or candidate.activated_epoch > candidate.trust_epoch
        ):
            return TrustResult(TrustDecision.BLOCK, ("invalid_trust_root",))
        if candidate.retired_epoch is not None and candidate.retired_epoch < candidate.activated_epoch:
            return TrustResult(TrustDecision.BLOCK, ("invalid_retirement_boundary",))
        if candidate.compromised_epoch is not None and candidate.compromised_epoch < candidate.activated_epoch:
            return TrustResult(TrustDecision.BLOCK, ("invalid_compromise_boundary",))
        if candidate.status is TrustRootStatus.RETIRED and candidate.retired_epoch is None:
            return TrustResult(TrustDecision.BLOCK, ("missing_retirement_boundary",))
        if candidate.status is TrustRootStatus.COMPROMISED and candidate.compromised_epoch is None:
            return TrustResult(TrustDecision.BLOCK, ("missing_compromise_boundary",))

    visiting: set[str] = set()
    seen: set[str] = set()

    def validate_lineage(node: TrustRoot) -> bool:
        if node.root_id in seen:
            return True
        if node.root_id in visiting:
            return False
        visiting.add(node.root_id)
        if node.parent_root_id is not None:
            parent = by_id.get(node.parent_root_id)
            if parent is None:
                return False
            if node.trust_epoch <= parent.trust_epoch:
                return False
            if not validate_lineage(parent):
                return False
        visiting.remove(node.root_id)
        seen.add(node.root_id)
        return True

    if not validate_lineage(root):
        return TrustResult(TrustDecision.BLOCK, ("invalid_trust_lineage",))

    if (
        not artifact.artifact_id
        or artifact.issued_epoch < 0
        or artifact.expires_epoch < artifact.issued_epoch
        or min(
            artifact.trust_epoch,
            artifact.authority_epoch,
            artifact.logical_epoch,
            artifact.state_version,
        ) < 0
    ):
        return TrustResult(TrustDecision.BLOCK, ("invalid_signed_artifact",))

    if artifact.trust_epoch != root.trust_epoch:
        return TrustResult(TrustDecision.BLOCK, ("artifact_root_epoch_mismatch",))

    if artifact.trust_epoch > context.current_trust_epoch:
        return TrustResult(TrustDecision.BLOCK, ("future_trust_epoch",))
    if artifact.authority_epoch > context.current_authority_epoch:
        return TrustResult(TrustDecision.BLOCK, ("future_authority_epoch",))
    if artifact.logical_epoch > context.current_logical_epoch:
        return TrustResult(TrustDecision.BLOCK, ("future_logical_epoch",))
    if artifact.state_version > context.current_state_version:
        return TrustResult(TrustDecision.BLOCK, ("future_state_version",))

    if root.status is TrustRootStatus.COMPROMISED:
        assert root.compromised_epoch is not None
        if artifact.issued_epoch >= root.compromised_epoch:
            return TrustResult(TrustDecision.BLOCK, ("issued_after_compromise",))
        return TrustResult(TrustDecision.BLOCK, ("compromised_root_not_admissible",))

    if artifact.issued_epoch < root.activated_epoch:
        return TrustResult(TrustDecision.BLOCK, ("issued_before_root_activation",))

    if root.status is TrustRootStatus.RETIRED:
        assert root.retired_epoch is not None
        if artifact.issued_epoch >= root.retired_epoch:
            return TrustResult(TrustDecision.BLOCK, ("issued_after_retirement",))
        return TrustResult(TrustDecision.STALE, ("retired_root",))

    if artifact.trust_epoch < context.current_trust_epoch:
        return TrustResult(TrustDecision.STALE, ("trust_epoch_stale",))
    if artifact.authority_epoch < context.current_authority_epoch:
        return TrustResult(TrustDecision.STALE, ("authority_epoch_stale",))
    if artifact.logical_epoch < context.current_logical_epoch:
        return TrustResult(TrustDecision.STALE, ("logical_epoch_stale",))
    if artifact.state_version < context.current_state_version:
        return TrustResult(TrustDecision.STALE, ("state_version_stale",))
    if context.current_logical_epoch > artifact.expires_epoch:
        return TrustResult(TrustDecision.STALE, ("artifact_expired",))
    if context.current_logical_epoch < artifact.issued_epoch:
        return TrustResult(TrustDecision.BLOCK, ("artifact_from_future",))

    return TrustResult(TrustDecision.ALLOW)
