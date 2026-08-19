from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from typing import Iterable, Mapping


class ProvenanceDecision(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class ProvenancePolicy:
    provenance_policy_id: str
    trusted_root_ids: frozenset[str]
    trusted_verifier_ids: frozenset[str]
    revoked_node_ids: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ProvenanceNode:
    node_id: str
    parent_ids: frozenset[str]
    subject_id: str
    subject_state_id: str
    verification_context_id: str
    policy_bundle_id: str
    verifier_id: str
    payload_digest: str
    evidence_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProvenanceResult:
    decision: ProvenanceDecision
    reasons: tuple[str, ...] = ()
    provenance_root: str | None = None


def _root(nodes: Iterable[ProvenanceNode]) -> str:
    rows: list[str] = []
    for node in sorted(nodes, key=lambda item: item.node_id):
        rows.append(
            "\0".join(
                (
                    node.node_id,
                    ",".join(sorted(node.parent_ids)),
                    node.subject_id,
                    node.subject_state_id,
                    node.verification_context_id,
                    node.policy_bundle_id,
                    node.verifier_id,
                    node.payload_digest,
                    node.evidence_id or "",
                )
            )
        )
    return hashlib.sha256(("oma:provenance:v1\0" + "\n".join(rows)).encode("utf-8")).hexdigest()


def evaluate_provenance(
    policy: ProvenancePolicy,
    nodes: Iterable[ProvenanceNode],
    *,
    subject_id: str,
    subject_state_id: str,
    verification_context_id: str,
    policy_bundle_id: str,
    required_evidence_ids: frozenset[str],
    required_evidence_digests: Mapping[str, str] | None = None,
) -> ProvenanceResult:
    items = tuple(nodes)
    if (
        not policy.provenance_policy_id
        or not policy.trusted_root_ids
        or not policy.trusted_verifier_ids
        or not subject_id
        or not subject_state_id
        or not verification_context_id
        or not policy_bundle_id
    ):
        return ProvenanceResult(ProvenanceDecision.BLOCK, ("invalid_provenance_context",))

    if required_evidence_digests is not None and set(required_evidence_digests) != set(required_evidence_ids):
        return ProvenanceResult(ProvenanceDecision.BLOCK, ("evidence_digest_set_mismatch",))

    ids = [node.node_id for node in items]
    if not ids or not all(ids) or len(ids) != len(set(ids)):
        return ProvenanceResult(ProvenanceDecision.BLOCK, ("invalid_or_duplicate_provenance_node",))
    by_id = {node.node_id: node for node in items}

    if not policy.trusted_root_ids <= by_id.keys():
        return ProvenanceResult(ProvenanceDecision.BLOCK, ("missing_trusted_provenance_root",))
    if policy.revoked_node_ids - by_id.keys():
        return ProvenanceResult(ProvenanceDecision.BLOCK, ("unknown_revoked_provenance_node",))

    evidence_nodes: dict[str, ProvenanceNode] = {}
    for node in items:
        if (
            not node.verifier_id
            or not node.payload_digest
            or node.subject_id != subject_id
            or node.subject_state_id != subject_state_id
            or node.verification_context_id != verification_context_id
            or node.policy_bundle_id != policy_bundle_id
        ):
            return ProvenanceResult(ProvenanceDecision.BLOCK, (f"provenance_binding_mismatch:{node.node_id}",))
        if node.verifier_id not in policy.trusted_verifier_ids:
            return ProvenanceResult(ProvenanceDecision.BLOCK, (f"untrusted_verifier:{node.node_id}",))
        if node.node_id in policy.revoked_node_ids:
            return ProvenanceResult(ProvenanceDecision.BLOCK, (f"revoked_provenance_node:{node.node_id}",))
        if node.node_id in policy.trusted_root_ids and node.parent_ids:
            return ProvenanceResult(ProvenanceDecision.BLOCK, (f"trusted_root_has_parent:{node.node_id}",))
        if node.node_id not in policy.trusted_root_ids and not node.parent_ids:
            return ProvenanceResult(ProvenanceDecision.BLOCK, (f"unrooted_provenance_node:{node.node_id}",))
        if any(parent_id not in by_id for parent_id in node.parent_ids):
            return ProvenanceResult(ProvenanceDecision.BLOCK, (f"missing_provenance_parent:{node.node_id}",))
        if node.evidence_id is not None:
            if not node.evidence_id:
                return ProvenanceResult(ProvenanceDecision.BLOCK, (f"invalid_evidence_binding:{node.node_id}",))
            if node.evidence_id in evidence_nodes:
                return ProvenanceResult(ProvenanceDecision.BLOCK, (f"duplicate_evidence_provenance:{node.evidence_id}",))
            if required_evidence_digests is not None and required_evidence_digests.get(node.evidence_id) != node.payload_digest:
                return ProvenanceResult(ProvenanceDecision.BLOCK, (f"evidence_payload_digest_mismatch:{node.evidence_id}",))
            evidence_nodes[node.evidence_id] = node

    if set(evidence_nodes) != set(required_evidence_ids):
        missing = sorted(required_evidence_ids - evidence_nodes.keys())
        extra = sorted(evidence_nodes.keys() - required_evidence_ids)
        reasons = tuple(
            [
                *(f"missing_evidence_provenance:{item}" for item in missing),
                *(f"unexpected_evidence_provenance:{item}" for item in extra),
            ]
        )
        return ProvenanceResult(ProvenanceDecision.BLOCK, reasons)

    visiting: set[str] = set()
    visited: set[str] = set()
    reaches_root: dict[str, bool] = {}

    def visit(node_id: str) -> bool | None:
        if node_id in visiting:
            return None
        if node_id in visited:
            return reaches_root[node_id]
        visiting.add(node_id)
        node = by_id[node_id]
        if node_id in policy.trusted_root_ids:
            ok = True
        else:
            ok = False
            for parent_id in node.parent_ids:
                parent_ok = visit(parent_id)
                if parent_ok is None:
                    return None
                ok = ok or parent_ok
        visiting.remove(node_id)
        visited.add(node_id)
        reaches_root[node_id] = ok
        return ok

    for node in items:
        result = visit(node.node_id)
        if result is None:
            return ProvenanceResult(ProvenanceDecision.BLOCK, ("provenance_cycle",))
        if not result:
            return ProvenanceResult(ProvenanceDecision.BLOCK, (f"provenance_not_rooted:{node.node_id}",))

    closure: set[str] = set()

    def collect(node_id: str) -> None:
        if node_id in closure:
            return
        closure.add(node_id)
        for parent_id in by_id[node_id].parent_ids:
            collect(parent_id)

    for node in evidence_nodes.values():
        collect(node.node_id)
    if closure != set(by_id):
        return ProvenanceResult(ProvenanceDecision.BLOCK, ("provenance_contains_unrelated_nodes",))

    return ProvenanceResult(ProvenanceDecision.ALLOW, (), _root(items))
