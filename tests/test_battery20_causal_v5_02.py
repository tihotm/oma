from oma.acceptance import AcceptanceContext, AcceptanceDecision, Evidence, evaluate_acceptance


def test_empty_evidence_id_currently_accepts():
    context = AcceptanceContext("subject", "state", "ctx", "bundle", frozenset({"o1"}))
    evidence = Evidence("", "o1", "subject", "state", "ctx", "bundle", True)
    result = evaluate_acceptance(context, (evidence,))
    assert result.decision is AcceptanceDecision.ACCEPT
