from oma.acceptance import AcceptanceContext, AcceptanceDecision, Evidence, evaluate_acceptance


def test_truthy_non_boolean_pass_flag_currently_accepts():
    context = AcceptanceContext("subject", "state", "ctx", "bundle", frozenset({"o1"}))
    evidence = Evidence("e1", "o1", "subject", "state", "ctx", "bundle", 1)
    result = evaluate_acceptance(context, (evidence,))
    assert result.decision is AcceptanceDecision.ACCEPT
