from oma.validation import (
    ValidationDecision,
    ValidationGraph,
    ValidationNode,
    ValidationObservation,
    canonical_validation_graph,
    evaluate_validation_graph,
    required_closure,
)


def obs(node_id: str, decision: ValidationDecision = ValidationDecision.ACCEPT, *, root: str | None = None):
    return ValidationObservation(node_id=node_id, decision=decision, evidence_root=root or f"root:{node_id}")


def full_accepting_observations(graph: ValidationGraph):
    return [obs(node_id) for node_id in sorted(required_closure(graph))]


def test_canonical_graph_contains_full_pipeline():
    graph = canonical_validation_graph()
    closure = required_closure(graph)
    assert len(closure) == 15
    assert "parse_schema" in closure
    assert "scope_integrity" in closure
    assert "trust_temporal" in closure
    assert "obligation_integrity" in closure
    assert "atomic_commit" in closure


def test_full_closure_accepts():
    graph = canonical_validation_graph()
    result = evaluate_validation_graph(graph, full_accepting_observations(graph))
    assert result.decision is ValidationDecision.ACCEPT


def test_missing_dependency_is_not_done():
    graph = canonical_validation_graph()
    items = full_accepting_observations(graph)
    items = [item for item in items if item.node_id != "authority_capability"]
    result = evaluate_validation_graph(graph, items)
    assert result.decision is ValidationDecision.NOT_DONE


def test_parse_cannot_be_skipped():
    graph = canonical_validation_graph()
    items = [item for item in full_accepting_observations(graph) if item.node_id != "parse_schema"]
    assert evaluate_validation_graph(graph, items).decision is ValidationDecision.NOT_DONE


def test_commit_authorization_cannot_be_skipped():
    graph = canonical_validation_graph()
    items = [item for item in full_accepting_observations(graph) if item.node_id != "commit_authorization"]
    assert evaluate_validation_graph(graph, items).decision is ValidationDecision.NOT_DONE


def test_atomic_commit_cannot_be_skipped():
    graph = canonical_validation_graph()
    items = [item for item in full_accepting_observations(graph) if item.node_id != "atomic_commit"]
    assert evaluate_validation_graph(graph, items).decision is ValidationDecision.NOT_DONE


def test_block_precedes_stale_not_done_accept():
    graph = canonical_validation_graph()
    items = full_accepting_observations(graph)
    items = [
        obs(item.node_id, ValidationDecision.BLOCK if item.node_id == "identity_namespace" else (
            ValidationDecision.STALE if item.node_id == "snapshot_freshness" else (
                ValidationDecision.NOT_DONE if item.node_id == "aggregation" else ValidationDecision.ACCEPT
            )
        ))
        for item in items
    ]
    assert evaluate_validation_graph(graph, items).decision is ValidationDecision.BLOCK


def test_stale_precedes_not_done_accept():
    graph = canonical_validation_graph()
    items = full_accepting_observations(graph)
    items = [
        obs(item.node_id, ValidationDecision.STALE if item.node_id == "snapshot_freshness" else (
            ValidationDecision.NOT_DONE if item.node_id == "aggregation" else ValidationDecision.ACCEPT
        ))
        for item in items
    ]
    assert evaluate_validation_graph(graph, items).decision is ValidationDecision.STALE


def test_not_done_precedes_accept():
    graph = canonical_validation_graph()
    items = [
        obs(item.node_id, ValidationDecision.NOT_DONE if item.node_id == "terminal_barrier" else ValidationDecision.ACCEPT)
        for item in full_accepting_observations(graph)
    ]
    assert evaluate_validation_graph(graph, items).decision is ValidationDecision.NOT_DONE


def test_duplicate_observation_blocks():
    graph = canonical_validation_graph()
    items = full_accepting_observations(graph)
    items.append(obs("parse_schema"))
    assert evaluate_validation_graph(graph, items).decision is ValidationDecision.BLOCK


def test_unknown_observation_blocks():
    graph = canonical_validation_graph()
    items = full_accepting_observations(graph) + [obs("hidden_bypass")]
    assert evaluate_validation_graph(graph, items).decision is ValidationDecision.BLOCK


def test_missing_evidence_root_blocks():
    graph = canonical_validation_graph()
    items = full_accepting_observations(graph)
    items = [ValidationObservation(i.node_id, i.decision, "" if i.node_id == "provenance" else i.evidence_root) for i in items]
    assert evaluate_validation_graph(graph, items).decision is ValidationDecision.BLOCK


def test_graph_cycle_blocks():
    graph = ValidationGraph(
        validation_graph_id="g",
        nodes=(ValidationNode("a", frozenset({"b"})), ValidationNode("b", frozenset({"a"}))),
        terminal_node_id="a",
    )
    assert evaluate_validation_graph(graph, []).decision is ValidationDecision.BLOCK


def test_self_dependency_blocks():
    graph = ValidationGraph("g", (ValidationNode("a", frozenset({"a"})),), "a")
    assert evaluate_validation_graph(graph, []).decision is ValidationDecision.BLOCK


def test_unknown_dependency_blocks():
    graph = ValidationGraph("g", (ValidationNode("a", frozenset({"missing"})),), "a")
    assert evaluate_validation_graph(graph, []).decision is ValidationDecision.BLOCK


def test_missing_terminal_node_blocks():
    graph = ValidationGraph("g", (ValidationNode("a"),), "missing")
    assert evaluate_validation_graph(graph, []).decision is ValidationDecision.BLOCK


def test_duplicate_node_id_blocks():
    graph = ValidationGraph("g", (ValidationNode("a"), ValidationNode("a")), "a")
    assert evaluate_validation_graph(graph, []).decision is ValidationDecision.BLOCK


def test_empty_graph_id_blocks():
    graph = ValidationGraph("", (ValidationNode("a"),), "a")
    assert evaluate_validation_graph(graph, []).decision is ValidationDecision.BLOCK


def test_observation_outside_terminal_closure_blocks():
    graph = ValidationGraph(
        "g",
        (
            ValidationNode("parse"),
            ValidationNode("commit", frozenset({"parse"})),
            ValidationNode("unrelated"),
        ),
        "commit",
    )
    result = evaluate_validation_graph(graph, [obs("parse"), obs("commit"), obs("unrelated")])
    assert result.decision is ValidationDecision.BLOCK


def test_closure_is_transitive():
    graph = ValidationGraph(
        "g",
        (
            ValidationNode("a"),
            ValidationNode("b", frozenset({"a"})),
            ValidationNode("c", frozenset({"b"})),
        ),
        "c",
    )
    assert required_closure(graph) == frozenset({"a", "b", "c"})


def test_irrelevant_nodes_are_not_required():
    graph = ValidationGraph(
        "g",
        (ValidationNode("a"), ValidationNode("commit", frozenset({"a"})), ValidationNode("x")),
        "commit",
    )
    result = evaluate_validation_graph(graph, [obs("a"), obs("commit")])
    assert result.decision is ValidationDecision.ACCEPT


def test_multiple_block_reasons_are_deterministic():
    graph = canonical_validation_graph()
    items = [
        obs(item.node_id, ValidationDecision.BLOCK if item.node_id in {"identity_namespace", "authority_capability"} else ValidationDecision.ACCEPT)
        for item in full_accepting_observations(graph)
    ]
    result = evaluate_validation_graph(graph, items)
    assert result.reasons == ("block:authority_capability", "block:identity_namespace")


def test_multiple_stale_reasons_are_deterministic():
    graph = canonical_validation_graph()
    items = [
        obs(item.node_id, ValidationDecision.STALE if item.node_id in {"snapshot_freshness", "retry_recovery"} else ValidationDecision.ACCEPT)
        for item in full_accepting_observations(graph)
    ]
    result = evaluate_validation_graph(graph, items)
    assert result.reasons == ("stale:retry_recovery", "stale:snapshot_freshness")


def test_validation_closure_root_is_stable_sorted_tuple():
    graph = canonical_validation_graph()
    result = evaluate_validation_graph(graph, full_accepting_observations(graph))
    assert result.validation_closure_root == tuple(sorted(result.validation_closure_root))
    assert len(result.validation_closure_root) == 15
