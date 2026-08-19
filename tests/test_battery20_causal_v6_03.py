from oma.validation import ValidationDecision, ValidationGraph, ValidationNode, ValidationObservation, evaluate_validation_graph


def test_03_observation_outside_terminal_closure_blocks():
    graph = ValidationGraph("g", (ValidationNode("a"), ValidationNode("b"), ValidationNode("c", frozenset({"a"}))), "c")
    result = evaluate_validation_graph(graph, (
        ValidationObservation("a", ValidationDecision.ACCEPT, "ra"),
        ValidationObservation("b", ValidationDecision.ACCEPT, "rb"),
        ValidationObservation("c", ValidationDecision.ACCEPT, "rc"),
    ))
    assert result.decision is ValidationDecision.BLOCK
