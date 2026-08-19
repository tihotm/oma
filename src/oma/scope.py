from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Iterable


class ScopeDecision(StrEnum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class ScopePolicy:
    scope_policy_id: str
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...] = ()
    protected_roles: frozenset[str] = frozenset()
    review_roles: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class FileTransition:
    path: str
    before_digest: str | None
    after_digest: str | None
    roles: frozenset[str] = frozenset()
    touched: bool = True


@dataclass(frozen=True, slots=True)
class ScopeResult:
    decision: ScopeDecision
    reasons: tuple[str, ...] = ()


def _normalize(path: str) -> str | None:
    raw = path.replace("\\", "/")
    candidate = PurePosixPath(raw)
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        return None
    normalized = candidate.as_posix().lstrip("./")
    if not normalized or normalized == ".":
        return None
    return normalized


def _matches(path: str, prefixes: tuple[str, ...]) -> bool:
    for raw_prefix in prefixes:
        prefix = _normalize(raw_prefix)
        if prefix is None:
            continue
        if path == prefix or path.startswith(prefix.rstrip("/") + "/"):
            return True
    return False


def evaluate_scope(
    policy: ScopePolicy,
    transitions: Iterable[FileTransition],
) -> ScopeResult:
    """Evaluate scope and transition integrity for one candidate change.

    The gate is history-aware: protected/review surfaces remain visible even
    when their final digest equals their initial digest (touch-and-restore).
    """
    items = tuple(transitions)
    if not policy.scope_policy_id:
        return ScopeResult(ScopeDecision.BLOCK, ("missing_scope_policy_id",))
    if not policy.allowed_paths:
        return ScopeResult(ScopeDecision.BLOCK, ("empty_allowed_scope",))

    normalized_allowed = tuple(filter(None, (_normalize(p) for p in policy.allowed_paths)))
    if len(normalized_allowed) != len(policy.allowed_paths):
        return ScopeResult(ScopeDecision.BLOCK, ("invalid_allowed_path",))
    if any(_normalize(p) is None for p in policy.forbidden_paths):
        return ScopeResult(ScopeDecision.BLOCK, ("invalid_forbidden_path",))

    review_reasons: list[str] = []

    for item in items:
        path = _normalize(item.path)
        if path is None:
            return ScopeResult(ScopeDecision.BLOCK, (f"invalid_path:{item.path}",))

        changed = item.before_digest != item.after_digest
        if changed and not item.touched:
            return ScopeResult(
                ScopeDecision.BLOCK,
                (f"transition_history_inconsistent:{path}",),
            )
        if not item.touched:
            continue

        if _matches(path, policy.forbidden_paths):
            return ScopeResult(ScopeDecision.BLOCK, (f"forbidden_path:{path}",))
        if not _matches(path, policy.allowed_paths):
            return ScopeResult(ScopeDecision.BLOCK, (f"scope_expansion:{path}",))

        protected = sorted(item.roles & policy.protected_roles)
        if protected:
            return ScopeResult(
                ScopeDecision.BLOCK,
                tuple(f"protected_role_touch:{role}:{path}" for role in protected),
            )

        review = sorted(item.roles & policy.review_roles)
        review_reasons.extend(f"sensitive_role_touch:{role}:{path}" for role in review)

    if review_reasons:
        return ScopeResult(ScopeDecision.REVIEW, tuple(sorted(set(review_reasons))))

    return ScopeResult(ScopeDecision.ALLOW)
