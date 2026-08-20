from oma.validation import ValidationDecision, ValidationGraph, ValidationNode, ValidationObservation, validation_observation_digest


def test_v11_13_digest_does_not_bind_full_graph_structure():
    observation = ValidationObservation("a", ValidationDecision.ACCEPT, "root:1")
    left = ValidationGraph("graph:1", (ValidationNode("a"),), "a")
    right = ValidationGraph(
        "graph:1",
        (ValidationNode("a", frozenset({"b"})), ValidationNode("b")),
        "a",
    )
    assert left != right
    assert validation_observation_digest(left, (observation,), domain="precommit") == validation_observation_digest(right, (observation,), domain="precommit")
