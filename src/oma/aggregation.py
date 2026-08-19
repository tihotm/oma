from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from typing import Iterable


class AggregationDecision(StrEnum):
    ALLOW = "ALLOW"
    NOT_DONE = "NOT_DONE"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class AggregationPolicy:
    aggregation_policy_id: str
    expected_evidence_set_id: str
    expected_evidence_ids: frozenset[str]
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    pair_id: str
    run_id: str


@dataclass(frozen=True, slots=True)
class AggregationItem:
    evidence_id: str
    payload_digest: str
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    pair_id: str
    run_id: str
    passed: bool


@dataclass(frozen=True, slots=True)
class AggregationResult:
    decision: AggregationDecision
    reasons: tuple[str, ...] = ()
    aggregation_root: str | None = None


def aggregation_root(policy: AggregationPolicy, items: Iterable[AggregationItem]) -> str:
    policy_row = "\0".join(
        (
            policy.aggregation_policy_id,
            policy.expected_evidence_set_id,
            ",".join(sorted(policy.expected_evidence_ids)),
            policy.subject_id,
            policy.subject_state_id,
            policy.verification_context_id,
            policy.policy_bundle_id,
            policy.pair_id,
            policy.run_id,
        )
    )
    item_rows = [
        "\0".join(
            (
                item.evidence_id,
                item.payload_digest,
                item.subject_id,
                item.subject_state_id,
                item.verification_context_id,
                item.policy_bundle_id,
                item.pair_id,
                item.run_id,
                "1" if item.passed else "0",
            )
        )
        for item in sorted(items, key=lambda item: item.evidence_id)
    ]
    payload = ("oma:aggregation:v1\0" + policy_row + "\n" + "\n".join(item_rows)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def evaluate_aggregation(
    policy: AggregationPolicy,
    items: Iterable[AggregationItem],
) -> AggregationResult:
    evidence = tuple(items)
    if (
        not policy.aggregation_policy_id
        or not policy.expected_evidence_set_id
        or not policy.expected_evidence_ids
        or not policy.subject_id
        or not policy.subject_state_id
        or not policy.verification_context_id
        or not policy.policy_bundle_id
        or not policy.pair_id
        or not policy.run_id
    ):
        return AggregationResult(AggregationDecision.BLOCK, ("invalid_aggregation_policy",))

    ids = [item.evidence_id for item in evidence]
    if not all(ids) or len(ids) != len(set(ids)):
        return AggregationResult(AggregationDecision.BLOCK, ("invalid_or_duplicate_aggregation_evidence",))

    present = set(ids)
    unexpected = sorted(present - policy.expected_evidence_ids)
    if unexpected:
        return AggregationResult(
            AggregationDecision.BLOCK,
            tuple(f"unexpected_aggregation_evidence:{item}" for item in unexpected),
        )

    for item in evidence:
        if not item.payload_digest:
            return AggregationResult(AggregationDecision.BLOCK, (f"missing_payload_digest:{item.evidence_id}",))
        if item.subject_id != policy.subject_id:
            return AggregationResult(AggregationDecision.BLOCK, (f"aggregation_subject_mismatch:{item.evidence_id}",))
        if item.subject_state_id != policy.subject_state_id:
            return AggregationResult(AggregationDecision.BLOCK, (f"aggregation_state_mismatch:{item.evidence_id}",))
        if item.verification_context_id != policy.verification_context_id:
            return AggregationResult(AggregationDecision.BLOCK, (f"aggregation_verification_context_mismatch:{item.evidence_id}",))
        if item.policy_bundle_id != policy.policy_bundle_id:
            return AggregationResult(AggregationDecision.BLOCK, (f"aggregation_policy_bundle_mismatch:{item.evidence_id}",))
        if item.pair_id != policy.pair_id:
            return AggregationResult(AggregationDecision.BLOCK, (f"aggregation_pair_mismatch:{item.evidence_id}",))
        if item.run_id != policy.run_id:
            return AggregationResult(AggregationDecision.BLOCK, (f"aggregation_run_mismatch:{item.evidence_id}",))

    missing = sorted(policy.expected_evidence_ids - present)
    if missing:
        return AggregationResult(
            AggregationDecision.NOT_DONE,
            tuple(f"missing_expected_evidence:{item}" for item in missing),
        )

    failed = sorted(item.evidence_id for item in evidence if not item.passed)
    if failed:
        return AggregationResult(
            AggregationDecision.NOT_DONE,
            tuple(f"expected_evidence_failed:{item}" for item in failed),
            aggregation_root(policy, evidence),
        )

    return AggregationResult(
        AggregationDecision.ALLOW,
        (),
        aggregation_root(policy, evidence),
    )
