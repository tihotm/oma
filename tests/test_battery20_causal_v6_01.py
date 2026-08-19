from oma.validation import ValidationDecision, ValidationGraph, ValidationNode, ValidationObservation, validation_closure_digest


def _obs():
    return (
        ValidationObservation("a", ValidationDecision.ACCEPT, "ra"),
        ValidationObservation("b", ValidationDecision.ACCEPT, "rb"),
        ValidationObservation("c", ValidationDecision.ACCEPT, "rc"),
    )


def test_01_validation_topology_is_not_bound_into_closure_digest():
    linear = ValidationGraph("g", (ValidationNode("a"), ValidationNode("b", frozenset({"a"})), ValidationNode("c", frozenset({"b"}))), "c")
    strengthened = ValidationGraph("g", (ValidationNode("a"), ValidationNode("b", frozenset({"a"})), ValidationNode("c", frozenset({"a", "b"}))), "c")
    assert validation_closure_digest(linear, _obs()) == validation_closure_digest(strengthened, _obs())
