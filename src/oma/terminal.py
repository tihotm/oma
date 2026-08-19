from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from typing import Iterable

from .validation import ValidationDecision, ValidationObservation


class TerminalDecision(StrEnum):
    ALLOW = "ALLOW"
    NOT_DONE = "NOT_DONE"
    STALE = "STALE"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class TerminalPolicy:
    termination_policy_id: str
    required_node_ids: frozenset[str]
    allowed_actions: frozenset[str] = frozenset({"DONE", "COMMIT"})


@dataclass(frozen=True, slots=True)
class TerminalResult:
    decision: TerminalDecision
    reasons: tuple[str, ...] = ()
    terminal_barrier_root: str | None = None


_CANONICAL_PRE_TERMINAL_NODES = frozenset(
    {
        "parse_schema",
        "identity_namespace",
        "scope_integrity",
        "authority_capability",
        "trust_temporal",
        "policy_bundle",
        "snapshot_freshness",
        "provenance",
        "obligation_integrity",
        "evidence_qualification",
        "aggregation",
        "retry_recovery",
    }
)


def canonical_terminal_policy(termination_policy_id: str) -> TerminalPolicy:
    return TerminalPolicy(
        termination_policy_id=termination_policy_id,
        required_node_ids=_CANONICAL_PRE_TERMINAL_NODES,
    )


def _barrier_root(
    policy: TerminalPolicy,
    action: str,
    observations: Iterable[ValidationObservation],
) -> str:
    rows = [
        "\0".join((item.node_id, item.decision.value, item.evidence_root))
        for item in sorted(observations, key=lambda value: value.node_id)
    ]
    payload = "\0".join(
        (
            "oma:terminal-barrier:v1",
            policy.termination_policy_id,
            ",".join(sorted(policy.required_node_ids)),
            ",".join(sorted(policy.allowed_actions)),
            action,
            "\n".join(rows),
        )
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def evaluate_terminal_barrier(
    policy: TerminalPolicy,
    observations: Iterable[ValidationObservation],
    *,
    requested_action: str,
) -> TerminalResult:
    """Authorize terminalization only after every prerequisite is ACCEPT.

    A terminal request never upgrades a prerequisite. BLOCK dominates STALE,
    which dominates NOT_DONE. Only a complete, exact, accepting prerequisite
    set can cross the barrier.
    """
    if (
        not policy.termination_policy_id
        or not policy.required_node_ids
        or not policy.allowed_actions
        or not all(policy.required_node_ids)
        or not all(policy.allowed_actions)
    ):
        return TerminalResult(TerminalDecision.BLOCK, ("invalid_terminal_policy",))
    if not requested_action or requested_action not in policy.allowed_actions:
        return TerminalResult(TerminalDecision.BLOCK, ("terminal_action_not_allowed",))

    items = tuple(observations)
    ids = [item.node_id for item in items]
    if not all(ids) or len(ids) != len(set(ids)):
        return TerminalResult(TerminalDecision.BLOCK, ("invalid_or_duplicate_terminal_observation",))
    if any(not item.evidence_root for item in items):
        return TerminalResult(TerminalDecision.BLOCK, ("missing_terminal_evidence_root",))

    present = set(ids)
    unexpected = sorted(present - policy.required_node_ids)
    if unexpected:
        return TerminalResult(
            TerminalDecision.BLOCK,
            tuple(f"unexpected_terminal_prerequisite:{node_id}" for node_id in unexpected),
        )

    missing = sorted(policy.required_node_ids - present)
    if missing:
        return TerminalResult(
            TerminalDecision.NOT_DONE,
            tuple(f"missing_terminal_prerequisite:{node_id}" for node_id in missing),
        )

    by_id = {item.node_id: item for item in items}
    blocked = sorted(node_id for node_id in policy.required_node_ids if by_id[node_id].decision is ValidationDecision.BLOCK)
    if blocked:
        return TerminalResult(
            TerminalDecision.BLOCK,
            tuple(f"terminal_blocked:{node_id}" for node_id in blocked),
        )

    stale = sorted(node_id for node_id in policy.required_node_ids if by_id[node_id].decision is ValidationDecision.STALE)
    if stale:
        return TerminalResult(
            TerminalDecision.STALE,
            tuple(f"terminal_stale:{node_id}" for node_id in stale),
        )

    not_done = sorted(node_id for node_id in policy.required_node_ids if by_id[node_id].decision is ValidationDecision.NOT_DONE)
    if not_done:
        return TerminalResult(
            TerminalDecision.NOT_DONE,
            tuple(f"terminal_not_done:{node_id}" for node_id in not_done),
        )

    if any(by_id[node_id].decision is not ValidationDecision.ACCEPT for node_id in policy.required_node_ids):
        return TerminalResult(TerminalDecision.BLOCK, ("unknown_terminal_decision",))

    return TerminalResult(
        TerminalDecision.ALLOW,
        (),
        _barrier_root(policy, requested_action, items),
    )
