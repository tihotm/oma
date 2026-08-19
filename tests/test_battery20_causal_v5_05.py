from oma.acceptance import AcceptanceContext, AcceptanceDecision, Evidence, evaluate_acceptance


def test_exact_complete_acceptance_set_accepts():
    context = AcceptanceContext("subject", "state", "ctx", "bundle", frozenset({"o1", "o2"}))
    evidence = (
        Evidence("e1", "o1", "subject", "state", "ctx", "bundle", True),
        Evidence("e2", "o2", "subject", "state", "ctx", "bundle", True),
    )
    result = evaluate_acceptance(context, evidence)
    assert result.decision is AcceptanceDecision.ACCEPT
