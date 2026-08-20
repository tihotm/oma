from oma.validation import ValidationDecision, ValidationGraph, ValidationNode, ValidationObservation, validation_observation_digest


def test_v11_14_control_character_digest_domain_currently_hashes():
    graph = ValidationGraph("graph:1", (ValidationNode("a"),), "a")
    observation = ValidationObservation("a", ValidationDecision.ACCEPT, "root:1")
    assert validation_observation_digest(graph, (observation,), domain="pre\0commit") is not None
