from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class AuthorityDecision(StrEnum):
    ALLOW = "ALLOW"
    STALE = "STALE"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class AuthorityContext:
    authority_context_id: str
    authority_epoch: int
    now_epoch: int
    trusted_issuers: frozenset[str]


@dataclass(frozen=True, slots=True)
class Capability:
    capability_id: str
    issuer: str
    holder: str
    actions: frozenset[str]
    targets: frozenset[str]
    scopes: frozenset[str]
    authority_epoch: int
    not_before_epoch: int
    expires_epoch: int
    parent_capability_id: str | None = None


@dataclass(frozen=True, slots=True)
class AuthorityRequest:
    actor: str
    action: str
    target: str
    scope: str
    capability_id: str


@dataclass(frozen=True, slots=True)
class AuthorityResult:
    decision: AuthorityDecision
    reasons: tuple[str, ...] = ()


def _is_subset(child: Capability, parent: Capability) -> bool:
    return (
        child.actions <= parent.actions
        and child.targets <= parent.targets
        and child.scopes <= parent.scopes
        and child.not_before_epoch >= parent.not_before_epoch
        and child.expires_epoch <= parent.expires_epoch
    )


def evaluate_authority(
    context: AuthorityContext,
    capabilities: Iterable[Capability],
    request: AuthorityRequest,
) -> AuthorityResult:
    items = tuple(capabilities)
    if (
        not context.authority_context_id
        or context.authority_epoch < 0
        or context.now_epoch < 0
        or not context.trusted_issuers
    ):
        return AuthorityResult(AuthorityDecision.BLOCK, ("invalid_authority_context",))

    ids = [c.capability_id for c in items]
    if not all(ids) or len(ids) != len(set(ids)):
        return AuthorityResult(AuthorityDecision.BLOCK, ("invalid_or_duplicate_capability_id",))
    by_id = {c.capability_id: c for c in items}

    if request.capability_id not in by_id:
        return AuthorityResult(AuthorityDecision.BLOCK, ("unknown_capability",))
    if not request.actor or not request.action or not request.target or not request.scope:
        return AuthorityResult(AuthorityDecision.BLOCK, ("invalid_authority_request",))

    visiting: set[str] = set()
    validated: set[str] = set()

    def validate(cap: Capability) -> AuthorityResult | None:
        if cap.capability_id in validated:
            return None
        if cap.capability_id in visiting:
            return AuthorityResult(AuthorityDecision.BLOCK, ("capability_cycle",))
        visiting.add(cap.capability_id)

        if (
            not cap.issuer
            or not cap.holder
            or not cap.actions
            or not cap.targets
            or not cap.scopes
            or cap.authority_epoch < 0
            or cap.not_before_epoch < 0
            or cap.expires_epoch < cap.not_before_epoch
        ):
            return AuthorityResult(AuthorityDecision.BLOCK, ("invalid_capability",))

        if cap.authority_epoch > context.authority_epoch:
            return AuthorityResult(AuthorityDecision.BLOCK, ("future_authority_epoch",))
        if cap.authority_epoch < context.authority_epoch:
            return AuthorityResult(AuthorityDecision.STALE, ("authority_epoch_stale",))
        if context.now_epoch < cap.not_before_epoch:
            return AuthorityResult(AuthorityDecision.BLOCK, ("capability_not_yet_valid",))
        if context.now_epoch > cap.expires_epoch:
            return AuthorityResult(AuthorityDecision.STALE, ("capability_expired",))

        if cap.parent_capability_id is None:
            if cap.issuer not in context.trusted_issuers:
                return AuthorityResult(AuthorityDecision.BLOCK, ("untrusted_root_issuer",))
            if cap.issuer == cap.holder:
                return AuthorityResult(AuthorityDecision.BLOCK, ("root_self_authorization",))
        else:
            parent = by_id.get(cap.parent_capability_id)
            if parent is None:
                return AuthorityResult(AuthorityDecision.BLOCK, ("missing_parent_capability",))
            parent_result = validate(parent)
            if parent_result is not None:
                return parent_result
            if cap.issuer != parent.holder:
                return AuthorityResult(AuthorityDecision.BLOCK, ("delegation_issuer_mismatch",))
            if cap.holder == cap.issuer:
                return AuthorityResult(AuthorityDecision.BLOCK, ("self_delegation",))
            if not _is_subset(cap, parent):
                return AuthorityResult(AuthorityDecision.BLOCK, ("capability_escalation",))

        visiting.remove(cap.capability_id)
        validated.add(cap.capability_id)
        return None

    selected = by_id[request.capability_id]
    result = validate(selected)
    if result is not None:
        return result

    if request.actor != selected.holder:
        return AuthorityResult(AuthorityDecision.BLOCK, ("actor_not_capability_holder",))
    if request.action not in selected.actions:
        return AuthorityResult(AuthorityDecision.BLOCK, ("action_not_authorized",))
    if request.target not in selected.targets:
        return AuthorityResult(AuthorityDecision.BLOCK, ("target_not_authorized",))
    if request.scope not in selected.scopes:
        return AuthorityResult(AuthorityDecision.BLOCK, ("scope_not_authorized",))

    return AuthorityResult(AuthorityDecision.ALLOW)
