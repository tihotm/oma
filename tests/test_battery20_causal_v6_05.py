from oma.validation import ValidationDecision, ValidationGraph, ValidationNode, ValidationObservation, evaluate_validation_graph


def test_05_block_precedence_dominates_stale():
    graph = ValidationGraph("g", (ValidationNode("a"), ValidationNode("b", frozenset({"a"}))), "b")
    result = evaluate_validation_graph(graph, (
        ValidationObservation("a", ValidationDecision.STALE, "ra"),
        ValidationObservation("b", ValidationDecision.BLOCK, "rb"),
    ))
    assert result.decision is ValidationDecision.BLOCK
