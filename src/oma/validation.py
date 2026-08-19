from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class ValidationDecision(StrEnum):
    ACCEPT = "ACCEPT"
    NOT_DONE = "NOT_DONE"
    STALE = "STALE"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class ValidationNode:
    node_id: str
    depends_on: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ValidationGraph:
    validation_graph_id: str
    nodes: tuple[ValidationNode, ...]
    terminal_node_id: str


@dataclass(frozen=True, slots=True)
class ValidationObservation:
    node_id: str
    decision: ValidationDecision
    evidence_root: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    decision: ValidationDecision
    reasons: tuple[str, ...] = ()
    validation_closure_root: tuple[str, ...] = ()


_PRECEDENCE = {
    ValidationDecision.ACCEPT: 0,
    ValidationDecision.NOT_DONE: 1,
    ValidationDecision.STALE: 2,
    ValidationDecision.BLOCK: 3,
}


def _validate_graph(graph: ValidationGraph) -> tuple[dict[str, ValidationNode], str | None]:
    if not graph.validation_graph_id or not graph.nodes or not graph.terminal_node_id:
        return {}, "invalid_validation_graph"
    ids = [node.node_id for node in graph.nodes]
    if not all(ids) or len(ids) != len(set(ids)):
        return {}, "invalid_or_duplicate_validation_node"
    by_id = {node.node_id: node for node in graph.nodes}
    if graph.terminal_node_id not in by_id:
        return {}, "missing_terminal_node"
    for node in graph.nodes:
        if node.node_id in node.depends_on:
            return {}, "self_dependency"
        if any(dep not in by_id for dep in node.depends_on):
            return {}, "unknown_dependency"

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visited:
            return False
        if node_id in visiting:
            return True
        visiting.add(node_id)
        for dep in by_id[node_id].depends_on:
            if visit(dep):
                return True
        visiting.remove(node_id)
        visited.add(node_id)
        return False

    if any(visit(node_id) for node_id in by_id):
        return {}, "validation_graph_cycle"
    return by_id, None


def required_closure(graph: ValidationGraph) -> frozenset[str]:
    by_id, error = _validate_graph(graph)
    if error is not None:
        return frozenset()

    closure: set[str] = set()

    def collect(node_id: str) -> None:
        if node_id in closure:
            return
        closure.add(node_id)
        for dep in by_id[node_id].depends_on:
            collect(dep)

    collect(graph.terminal_node_id)
    return frozenset(closure)


def evaluate_validation_graph(
    graph: ValidationGraph,
    observations: Iterable[ValidationObservation],
) -> ValidationResult:
    by_id, error = _validate_graph(graph)
    if error is not None:
        return ValidationResult(ValidationDecision.BLOCK, (error,))

    items = tuple(observations)
    ids = [item.node_id for item in items]
    if len(ids) != len(set(ids)):
        return ValidationResult(ValidationDecision.BLOCK, ("duplicate_validation_observation",))
    if any(item.node_id not in by_id for item in items):
        return ValidationResult(ValidationDecision.BLOCK, ("unknown_validation_observation",))
    if any(not item.evidence_root for item in items):
        return ValidationResult(ValidationDecision.BLOCK, ("missing_validation_evidence_root",))

    closure = required_closure(graph)
    observed = {item.node_id: item for item in items}
    missing = sorted(closure - observed.keys())
    if missing:
        return ValidationResult(
            ValidationDecision.NOT_DONE,
            tuple(f"missing_validation:{node_id}" for node_id in missing),
            tuple(sorted(closure)),
        )

    irrelevant = set(observed) - closure
    if irrelevant:
        return ValidationResult(
            ValidationDecision.BLOCK,
            tuple(
                f"observation_outside_terminal_closure:{node_id}"
                for node_id in sorted(irrelevant)
            ),
            tuple(sorted(closure)),
        )

    worst = max(
        (observed[node_id].decision for node_id in closure),
        key=lambda decision: _PRECEDENCE[decision],
    )
    if worst is not ValidationDecision.ACCEPT:
        reasons = tuple(
            f"{observed[node_id].decision.value.lower()}:{node_id}"
            for node_id in sorted(closure)
            if observed[node_id].decision is worst
        )
        return ValidationResult(worst, reasons, tuple(sorted(closure)))

    return ValidationResult(
        ValidationDecision.ACCEPT,
        (),
        tuple(sorted(closure)),
    )


def canonical_validation_graph() -> ValidationGraph:
    names = (
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
        "terminal_barrier",
        "commit_authorization",
        "atomic_commit",
    )
    nodes: list[ValidationNode] = []
    previous: str | None = None
    for name in names:
        deps = frozenset() if previous is None else frozenset({previous})
        nodes.append(ValidationNode(name, deps))
        previous = name
    return ValidationGraph(
        validation_graph_id="oma:canonical-validation:v3",
        nodes=tuple(nodes),
        terminal_node_id="atomic_commit",
    )
