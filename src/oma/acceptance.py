from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class AcceptanceDecision(StrEnum):
    BLOCK = "BLOCK"
    NOT_DONE = "NOT_DONE"
    ACCEPT = "ACCEPT"


@dataclass(frozen=True, slots=True)
class AcceptanceContext:
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    required_obligations: frozenset[str]


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    obligation_id: str
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    passed: bool


@dataclass(frozen=True, slots=True)
class AcceptanceResult:
    decision: AcceptanceDecision
    reasons: tuple[str, ...] = ()


def evaluate_acceptance(
    context: AcceptanceContext,
    evidence: Iterable[Evidence],
) -> AcceptanceResult:
    """Evaluate the first implementation slice of OMA acceptance.

    Integrity failures fail closed as BLOCK. A well-formed but incomplete
    acceptance set is NOT_DONE. ACCEPT requires exactly one correctly bound,
    passing evidence record for every required obligation.
    """
    items = tuple(evidence)

    ids = [item.evidence_id for item in items]
    if len(ids) != len(set(ids)):
        return AcceptanceResult(AcceptanceDecision.BLOCK, ("duplicate_evidence_id",))

    obligation_ids = [item.obligation_id for item in items]
    if len(obligation_ids) != len(set(obligation_ids)):
        return AcceptanceResult(AcceptanceDecision.BLOCK, ("duplicate_obligation_evidence",))

    for item in items:
        if item.obligation_id not in context.required_obligations:
            return AcceptanceResult(AcceptanceDecision.BLOCK, ("unknown_obligation",))
        if item.subject_id != context.subject_id:
            return AcceptanceResult(AcceptanceDecision.BLOCK, ("subject_mismatch",))
        if item.subject_state_id != context.subject_state_id:
            return AcceptanceResult(AcceptanceDecision.BLOCK, ("subject_state_mismatch",))
        if item.verification_context_id != context.verification_context_id:
            return AcceptanceResult(AcceptanceDecision.BLOCK, ("verification_context_mismatch",))
        if item.policy_bundle_id != context.policy_bundle_id:
            return AcceptanceResult(AcceptanceDecision.BLOCK, ("policy_bundle_mismatch",))

    by_obligation = {item.obligation_id: item for item in items}
    missing = sorted(context.required_obligations - by_obligation.keys())
    if missing:
        return AcceptanceResult(
            AcceptanceDecision.NOT_DONE,
            tuple(f"missing_obligation:{obligation}" for obligation in missing),
        )

    failed = sorted(
        obligation for obligation, item in by_obligation.items() if not item.passed
    )
    if failed:
        return AcceptanceResult(
            AcceptanceDecision.NOT_DONE,
            tuple(f"failed_obligation:{obligation}" for obligation in failed),
        )

    return AcceptanceResult(AcceptanceDecision.ACCEPT)
