from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum


class CommitDecision(StrEnum):
    ALLOW = "ALLOW"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class AcceptanceSnapshot:
    acceptance_snapshot_id: str
    subject_id: str
    subject_state_id: str
    policy_bundle_id: str
    obligation_root: str
    evidence_root: str
    ledger_head: str
    state_version: int
    terminal_epoch: int
    policy_bundle_root: str | None = None


@dataclass(frozen=True, slots=True)
class CommitToken:
    token_id: str
    acceptance_snapshot_id: str
    subject_id: str
    terminal_epoch: int
    single_use: bool = True


@dataclass(frozen=True, slots=True)
class CommitState:
    subject_id: str
    subject_state_id: str
    policy_bundle_id: str
    obligation_root: str
    evidence_root: str
    ledger_head: str
    state_version: int
    terminal_epoch: int
    consumed_token_ids: frozenset[str] = frozenset()
    terminal_commit_ids: frozenset[str] = frozenset()
    policy_bundle_root: str | None = None


@dataclass(frozen=True, slots=True)
class CommitResult:
    decision: CommitDecision
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CommitTransition:
    result: CommitResult
    state: CommitState


def evaluate_commit(
    snapshot: AcceptanceSnapshot,
    token: CommitToken,
    current: CommitState,
    *,
    terminal_commit_id: str,
) -> CommitResult:
    """Validate snapshot-bound, single-use terminal commit authorization.

    Integrity violations fail closed as BLOCK. A legitimate drift since
    verification is STALE. Replays or an already-finalized terminal epoch are
    CONFLICT. ALLOW means compare-and-swap preconditions still hold.
    """
    if (
        not snapshot.acceptance_snapshot_id
        or not snapshot.subject_id
        or snapshot.state_version < 0
        or snapshot.terminal_epoch < 0
    ):
        return CommitResult(CommitDecision.BLOCK, ("invalid_snapshot",))

    if not token.token_id or not terminal_commit_id:
        return CommitResult(CommitDecision.BLOCK, ("invalid_commit_identity",))
    if not token.single_use:
        return CommitResult(CommitDecision.BLOCK, ("token_not_single_use",))
    if token.acceptance_snapshot_id != snapshot.acceptance_snapshot_id:
        return CommitResult(CommitDecision.BLOCK, ("token_snapshot_mismatch",))
    if token.subject_id != snapshot.subject_id:
        return CommitResult(CommitDecision.BLOCK, ("token_subject_mismatch",))
    if token.terminal_epoch != snapshot.terminal_epoch:
        return CommitResult(CommitDecision.BLOCK, ("token_terminal_epoch_mismatch",))
    if current.subject_id != snapshot.subject_id:
        return CommitResult(CommitDecision.BLOCK, ("current_subject_mismatch",))

    if token.token_id in current.consumed_token_ids:
        return CommitResult(CommitDecision.CONFLICT, ("commit_token_replay",))
    if current.terminal_commit_ids:
        return CommitResult(CommitDecision.CONFLICT, ("terminal_already_committed",))

    if current.terminal_epoch != snapshot.terminal_epoch:
        return CommitResult(CommitDecision.STALE, ("terminal_epoch_drift",))

    drift_fields: list[str] = []
    for field in (
        "subject_state_id",
        "policy_bundle_id",
        "policy_bundle_root",
        "obligation_root",
        "evidence_root",
        "ledger_head",
        "state_version",
    ):
        if getattr(current, field) != getattr(snapshot, field):
            drift_fields.append(field)

    if drift_fields:
        return CommitResult(
            CommitDecision.STALE,
            tuple(f"snapshot_drift:{field}" for field in drift_fields),
        )

    return CommitResult(CommitDecision.ALLOW)


def commit_if_current(
    snapshot: AcceptanceSnapshot,
    token: CommitToken,
    current: CommitState,
    *,
    terminal_commit_id: str,
) -> CommitTransition:
    """Apply the in-memory CAS transition when authorization is still current.

    This models the atomic state transition required from a durable adapter:
    token consumption and terminal-record creation happen together. The
    durable storage implementation is intentionally a later layer.
    """
    result = evaluate_commit(
        snapshot,
        token,
        current,
        terminal_commit_id=terminal_commit_id,
    )
    if result.decision is not CommitDecision.ALLOW:
        return CommitTransition(result, current)

    next_state = replace(
        current,
        consumed_token_ids=current.consumed_token_ids | {token.token_id},
        terminal_commit_ids=current.terminal_commit_ids | {terminal_commit_id},
    )
    return CommitTransition(result, next_state)
