from oma.acceptance import AcceptanceContext, AcceptanceDecision, evaluate_acceptance


def test_empty_acceptance_denominator_currently_accepts():
    context = AcceptanceContext("subject", "state", "ctx", "bundle", frozenset())
    result = evaluate_acceptance(context, ())
    assert result.decision is AcceptanceDecision.ACCEPT
