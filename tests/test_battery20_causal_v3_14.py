from oma.validation import ValidationDecision, ValidationGraph, ValidationNode, evaluate_validation_graph


def test_14_validation_graph_cycle_blocks():
    graph = ValidationGraph(
        "g",
        (
            ValidationNode("a", frozenset({"b"})),
            ValidationNode("b", frozenset({"a"})),
        ),
        "b",
    )
    result = evaluate_validation_graph(graph, ())
    assert result.decision is ValidationDecision.BLOCK
    assert "validation_graph_cycle" in result.reasons
