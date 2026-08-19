from oma.validation import ValidationDecision, ValidationGraph, ValidationNode, ValidationObservation, evaluate_validation_graph


def test_04_missing_dependency_observation_is_not_done():
    graph = ValidationGraph("g", (ValidationNode("a"), ValidationNode("b", frozenset({"a"}))), "b")
    result = evaluate_validation_graph(graph, (ValidationObservation("b", ValidationDecision.ACCEPT, "rb"),))
    assert result.decision is ValidationDecision.NOT_DONE
