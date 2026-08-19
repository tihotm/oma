from oma.acceptance import AcceptanceContext, AcceptanceDecision, Evidence, evaluate_acceptance


def test_empty_acceptance_bindings_currently_accept_when_matching():
    context = AcceptanceContext("", "", "", "", frozenset({"o1"}))
    evidence = Evidence("e1", "o1", "", "", "", "", True)
    result = evaluate_acceptance(context, (evidence,))
    assert result.decision is AcceptanceDecision.ACCEPT
