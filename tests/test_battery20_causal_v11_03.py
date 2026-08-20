from oma.acceptance import AcceptanceContext, AcceptanceDecision, Evidence, evaluate_acceptance


def test_v11_03_empty_evidence_identifier_currently_accepts():
    context = AcceptanceContext("subject:1", "state:1", "verify:1", "bundle:1", frozenset({"ob:1"}))
    evidence = Evidence("", "ob:1", "subject:1", "state:1", "verify:1", "bundle:1", True)
    assert evaluate_acceptance(context, (evidence,)).decision is AcceptanceDecision.ACCEPT
