from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib


class ObligationDecision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class ObligationSpec:
    obligation_id: str
    requirement_digest: str
    strength: int = 1


@dataclass(frozen=True, slots=True)
class ObligationManifest:
    obligation_set_id: str
    obligations: tuple[ObligationSpec, ...]


@dataclass(frozen=True, slots=True)
class ObligationResult:
    decision: ObligationDecision
    reasons: tuple[str, ...] = ()
    obligation_root: str = ""
    required_obligations: frozenset[str] = frozenset()


def obligation_root(manifest: ObligationManifest) -> str:
    payload = [f"set:{manifest.obligation_set_id}"]
    for item in sorted(manifest.obligations, key=lambda x: x.obligation_id):
        payload.append(
            f"{item.obligation_id}\0{item.requirement_digest}\0{item.strength}"
        )
    return hashlib.sha256(
        b"oma:obligation-manifest:v1\0" + "\0".join(payload).encode("utf-8")
    ).hexdigest()


def _validate(
    manifest: ObligationManifest,
) -> tuple[dict[str, ObligationSpec], str | None]:
    if not manifest.obligation_set_id or not manifest.obligations:
        return {}, "invalid_obligation_manifest"
    ids = [item.obligation_id for item in manifest.obligations]
    if not all(ids) or len(ids) != len(set(ids)):
        return {}, "invalid_or_duplicate_obligation_id"
    for item in manifest.obligations:
        if not item.requirement_digest or item.strength < 1:
            return {}, "invalid_obligation_spec"
    return {item.obligation_id: item for item in manifest.obligations}, None


def evaluate_obligation_manifest(
    expected: ObligationManifest,
    presented: ObligationManifest,
    *,
    acceptance_required_obligations: frozenset[str],
) -> ObligationResult:
    """Protect the acceptance denominator against manifest laundering.

    The presented manifest must be exactly the immutable obligation set that
    acceptance is measured against. Legitimate manifest evolution requires a
    new obligation_set_id rather than mutating obligations in place.
    """
    expected_by_id, error = _validate(expected)
    if error:
        return ObligationResult(ObligationDecision.BLOCK, (f"expected:{error}",))
    presented_by_id, error = _validate(presented)
    if error:
        return ObligationResult(ObligationDecision.BLOCK, (f"presented:{error}",))

    if presented.obligation_set_id != expected.obligation_set_id:
        return ObligationResult(
            ObligationDecision.BLOCK, ("obligation_set_id_mismatch",)
        )

    missing = sorted(set(expected_by_id) - set(presented_by_id))
    if missing:
        return ObligationResult(
            ObligationDecision.BLOCK,
            tuple(f"missing_obligation:{item}" for item in missing),
        )

    unexpected = sorted(set(presented_by_id) - set(expected_by_id))
    if unexpected:
        return ObligationResult(
            ObligationDecision.BLOCK,
            tuple(f"unexpected_obligation:{item}" for item in unexpected),
        )

    reasons: list[str] = []
    for obligation_id in sorted(expected_by_id):
        expected_item = expected_by_id[obligation_id]
        presented_item = presented_by_id[obligation_id]
        if presented_item.requirement_digest != expected_item.requirement_digest:
            reasons.append(f"obligation_substitution:{obligation_id}")
        if presented_item.strength < expected_item.strength:
            reasons.append(f"obligation_downgrade:{obligation_id}")
        elif presented_item.strength > expected_item.strength:
            reasons.append(f"obligation_mutation:{obligation_id}")
    if reasons:
        return ObligationResult(ObligationDecision.BLOCK, tuple(reasons))

    expected_ids = frozenset(expected_by_id)
    if acceptance_required_obligations != expected_ids:
        missing_from_acceptance = sorted(
            expected_ids - acceptance_required_obligations
        )
        extra_in_acceptance = sorted(
            acceptance_required_obligations - expected_ids
        )
        denominator_reasons = [
            *(
                f"acceptance_denominator_missing:{item}"
                for item in missing_from_acceptance
            ),
            *(
                f"acceptance_denominator_unknown:{item}"
                for item in extra_in_acceptance
            ),
        ]
        return ObligationResult(
            ObligationDecision.BLOCK, tuple(denominator_reasons)
        )

    return ObligationResult(
        ObligationDecision.ALLOW,
        (),
        obligation_root(presented),
        expected_ids,
    )
