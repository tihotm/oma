from oma.acceptance import AcceptanceContext, AcceptanceDecision, Evidence, evaluate_acceptance


def test_v11_04_numeric_identity_currently_accepts_when_equal():
    context = AcceptanceContext(1, "state:1", "verify:1", "bundle:1", frozenset({"ob:1"}))
    evidence = Evidence("ev:1", "ob:1", 1, "state:1", "verify:1", "bundle:1", True)
    assert evaluate_acceptance(context, (evidence,)).decision is AcceptanceDecision.ACCEPT
