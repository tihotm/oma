from oma.validation import ValidationDecision, ValidationGraph, ValidationNode, ValidationObservation, evaluate_validation_graph


def test_v11_15_unknown_observation_still_blocks():
    graph = ValidationGraph("graph:1", (ValidationNode("a"),), "a")
    result = evaluate_validation_graph(
        graph,
        (
            ValidationObservation("a", ValidationDecision.ACCEPT, "root:a"),
            ValidationObservation("hidden", ValidationDecision.ACCEPT, "root:hidden"),
        ),
    )
    assert result.decision is ValidationDecision.BLOCK
