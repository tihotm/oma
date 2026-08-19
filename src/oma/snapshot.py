from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class SnapshotDecision(StrEnum):
    ALLOW = "ALLOW"
    STALE = "STALE"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class SnapshotResult:
    decision: SnapshotDecision
    reasons: tuple[str, ...] = ()


def evaluate_snapshot_freshness(snapshot: Any, current: Any) -> SnapshotResult:
    """Validate that acceptance-critical state is still the verified state.

    Rollback or malformed state is an integrity violation (BLOCK). Legitimate
    forward movement or binding drift makes the verified snapshot stale
    (STALE). Exact equality across acceptance-critical bindings is ALLOW.
    Token replay and terminal commit conflicts remain commit-gate concerns.
    """
    required_snapshot_strings = (
        "acceptance_snapshot_id",
        "subject_id",
        "subject_state_id",
        "policy_bundle_id",
        "obligation_root",
        "evidence_root",
        "ledger_head",
    )
    required_current_strings = (
        "subject_id",
        "subject_state_id",
        "policy_bundle_id",
        "obligation_root",
        "evidence_root",
        "ledger_head",
    )
    try:
        if any(not getattr(snapshot, field) for field in required_snapshot_strings):
            return SnapshotResult(SnapshotDecision.BLOCK, ("invalid_acceptance_snapshot",))
        if any(not getattr(current, field) for field in required_current_strings):
            return SnapshotResult(SnapshotDecision.BLOCK, ("invalid_current_snapshot_state",))
        if snapshot.state_version < 0 or snapshot.terminal_epoch < 0:
            return SnapshotResult(SnapshotDecision.BLOCK, ("invalid_acceptance_snapshot",))
        if current.state_version < 0 or current.terminal_epoch < 0:
            return SnapshotResult(SnapshotDecision.BLOCK, ("invalid_current_snapshot_state",))
    except (AttributeError, TypeError):
        return SnapshotResult(SnapshotDecision.BLOCK, ("invalid_snapshot_shape",))

    if current.subject_id != snapshot.subject_id:
        return SnapshotResult(SnapshotDecision.BLOCK, ("snapshot_subject_mismatch",))

    # Monotonic counters must never move backwards. This is stronger than
    # ordinary staleness because rollback can resurrect previously valid state.
    rollback: list[str] = []
    if current.state_version < snapshot.state_version:
        rollback.append("state_version")
    if current.terminal_epoch < snapshot.terminal_epoch:
        rollback.append("terminal_epoch")
    if rollback:
        return SnapshotResult(
            SnapshotDecision.BLOCK,
            tuple(f"snapshot_rollback:{field}" for field in rollback),
        )

    stale: list[str] = []
    if current.state_version > snapshot.state_version:
        stale.append("state_version")
    if current.terminal_epoch > snapshot.terminal_epoch:
        stale.append("terminal_epoch")

    for field in (
        "subject_state_id",
        "policy_bundle_id",
        "policy_bundle_root",
        "obligation_root",
        "evidence_root",
        "ledger_head",
    ):
        if getattr(current, field, None) != getattr(snapshot, field, None):
            stale.append(field)

    if stale:
        return SnapshotResult(
            SnapshotDecision.STALE,
            tuple(f"snapshot_stale:{field}" for field in stale),
        )

    return SnapshotResult(SnapshotDecision.ALLOW)
