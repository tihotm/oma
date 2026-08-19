from oma.validation import ValidationDecision, ValidationGraph, ValidationNode, ValidationObservation, validation_closure_digest


def test_02_validation_node_order_changes_digest():
    first = ValidationGraph("g", (ValidationNode("a"), ValidationNode("b", frozenset({"a"})), ValidationNode("c", frozenset({"b"}))), "c")
    second = ValidationGraph("g", (ValidationNode("b", frozenset({"a"})), ValidationNode("a"), ValidationNode("c", frozenset({"b"}))), "c")
    obs = (
        ValidationObservation("a", ValidationDecision.ACCEPT, "ra"),
        ValidationObservation("b", ValidationDecision.ACCEPT, "rb"),
        ValidationObservation("c", ValidationDecision.ACCEPT, "rc"),
    )
    assert validation_closure_digest(first, obs) != validation_closure_digest(second, obs)
