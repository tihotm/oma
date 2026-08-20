from oma.validation import ValidationDecision, ValidationGraph, ValidationNode, ValidationObservation, evaluate_validation_graph


def test_v11_11_control_character_node_identifier_currently_accepts():
    node_id = "parse\nshadow"
    graph = ValidationGraph("graph:1", (ValidationNode(node_id),), node_id)
    observation = ValidationObservation(node_id, ValidationDecision.ACCEPT, "root:1")
    assert evaluate_validation_graph(graph, (observation,)).decision is ValidationDecision.ACCEPT
