import pytest

from oma.validation import ValidationGraph, ValidationNode, ValidationObservation, evaluate_validation_graph


def test_v11_12_string_decision_raises_instead_of_blocking():
    graph = ValidationGraph("graph:1", (ValidationNode("a"),), "a")
    observation = ValidationObservation("a", "ACCEPT", "root:1")
    with pytest.raises(AttributeError):
        evaluate_validation_graph(graph, (observation,))
