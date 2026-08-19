from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class RetryDecision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class RetryEventKind(StrEnum):
    INITIAL = "INITIAL"
    RETRY = "RETRY"
    RECOVERY = "RECOVERY"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    retry_policy_id: str
    max_execution_attempts: int
    max_cumulative_cost: int
    authorized_retry_reasons: frozenset[str]
    authorized_recovery_reasons: frozenset[str]


@dataclass(frozen=True, slots=True)
class RetryDomain:
    retry_domain_id: str
    subject_id: str
    pair_id: str
    lineage_id: str
    retry_policy_id: str


@dataclass(frozen=True, slots=True)
class RetryEvent:
    event_id: str
    sequence: int
    kind: RetryEventKind
    attempt_number: int
    run_id: str
    subject_id: str
    pair_id: str
    lineage_id: str
    retry_domain_id: str
    retry_policy_id: str
    reason: str
    cost_units: int = 0


@dataclass(frozen=True, slots=True)
class RetryResult:
    decision: RetryDecision
    reasons: tuple[str, ...] = ()
    execution_attempts: int = 0
    cumulative_cost: int = 0


def evaluate_retry_domain(
    policy: RetryPolicy,
    domain: RetryDomain,
    events: Iterable[RetryEvent],
) -> RetryResult:
    """Validate retry/recovery history for one causal retry domain.

    Process/run boundaries do not reset attempt count, cumulative budget,
    lineage, subject, pair, or policy bindings.
    """
    items = tuple(events)

    if not policy.retry_policy_id or policy.retry_policy_id != domain.retry_policy_id:
        return RetryResult(RetryDecision.BLOCK, ("retry_policy_mismatch",))
    if policy.max_execution_attempts < 1:
        return RetryResult(RetryDecision.BLOCK, ("invalid_max_execution_attempts",))
    if policy.max_cumulative_cost < 0:
        return RetryResult(RetryDecision.BLOCK, ("invalid_max_cumulative_cost",))
    if not domain.retry_domain_id or not domain.subject_id or not domain.pair_id or not domain.lineage_id:
        return RetryResult(RetryDecision.BLOCK, ("invalid_retry_domain",))

    ids = [item.event_id for item in items]
    if len(ids) != len(set(ids)):
        return RetryResult(RetryDecision.BLOCK, ("duplicate_retry_event_id",))

    expected_sequences = list(range(1, len(items) + 1))
    actual_sequences = [item.sequence for item in items]
    if actual_sequences != expected_sequences:
        return RetryResult(RetryDecision.BLOCK, ("non_contiguous_event_sequence",))

    execution_attempts = 0
    cumulative_cost = 0
    seen_initial = False
    existing_attempts: set[int] = set()

    for item in items:
        if item.retry_domain_id != domain.retry_domain_id:
            return RetryResult(RetryDecision.BLOCK, ("retry_domain_mismatch",), execution_attempts, cumulative_cost)
        if item.retry_policy_id != domain.retry_policy_id:
            return RetryResult(RetryDecision.BLOCK, ("retry_policy_binding_mismatch",), execution_attempts, cumulative_cost)
        if item.subject_id != domain.subject_id:
            return RetryResult(RetryDecision.BLOCK, ("subject_mismatch",), execution_attempts, cumulative_cost)
        if item.pair_id != domain.pair_id:
            return RetryResult(RetryDecision.BLOCK, ("pair_mismatch",), execution_attempts, cumulative_cost)
        if item.lineage_id != domain.lineage_id:
            return RetryResult(RetryDecision.BLOCK, ("lineage_mismatch",), execution_attempts, cumulative_cost)
        if not item.run_id:
            return RetryResult(RetryDecision.BLOCK, ("missing_run_id",), execution_attempts, cumulative_cost)
        if item.cost_units < 0:
            return RetryResult(RetryDecision.BLOCK, ("negative_cost",), execution_attempts, cumulative_cost)

        cumulative_cost += item.cost_units
        if cumulative_cost > policy.max_cumulative_cost:
            return RetryResult(RetryDecision.BLOCK, ("cumulative_budget_exceeded",), execution_attempts, cumulative_cost)

        if item.kind is RetryEventKind.INITIAL:
            if seen_initial or item.sequence != 1 or item.attempt_number != 1:
                return RetryResult(RetryDecision.BLOCK, ("invalid_initial_attempt",), execution_attempts, cumulative_cost)
            if item.reason != "initial":
                return RetryResult(RetryDecision.BLOCK, ("invalid_initial_reason",), execution_attempts, cumulative_cost)
            seen_initial = True
            execution_attempts = 1
            existing_attempts.add(1)

        elif item.kind is RetryEventKind.RETRY:
            if not seen_initial:
                return RetryResult(RetryDecision.BLOCK, ("retry_without_initial",), execution_attempts, cumulative_cost)
            if item.reason not in policy.authorized_retry_reasons:
                return RetryResult(RetryDecision.BLOCK, ("unauthorized_retry_reason",), execution_attempts, cumulative_cost)
            expected_attempt = execution_attempts + 1
            if item.attempt_number != expected_attempt:
                return RetryResult(RetryDecision.BLOCK, ("attempt_sequence_reset_or_gap",), execution_attempts, cumulative_cost)
            execution_attempts = expected_attempt
            existing_attempts.add(expected_attempt)
            if execution_attempts > policy.max_execution_attempts:
                return RetryResult(RetryDecision.BLOCK, ("retry_attempt_limit_exceeded",), execution_attempts, cumulative_cost)

        elif item.kind is RetryEventKind.RECOVERY:
            if not seen_initial:
                return RetryResult(RetryDecision.BLOCK, ("recovery_without_initial",), execution_attempts, cumulative_cost)
            if item.reason not in policy.authorized_recovery_reasons:
                return RetryResult(RetryDecision.BLOCK, ("unauthorized_recovery_reason",), execution_attempts, cumulative_cost)
            if item.attempt_number not in existing_attempts:
                return RetryResult(RetryDecision.BLOCK, ("recovery_unknown_attempt",), execution_attempts, cumulative_cost)

        else:
            return RetryResult(RetryDecision.BLOCK, ("unknown_retry_event_kind",), execution_attempts, cumulative_cost)

    if items and not seen_initial:
        return RetryResult(RetryDecision.BLOCK, ("missing_initial_attempt",), execution_attempts, cumulative_cost)

    return RetryResult(RetryDecision.ALLOW, (), execution_attempts, cumulative_cost)
