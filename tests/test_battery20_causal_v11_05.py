from oma.acceptance import AcceptanceContext, AcceptanceDecision, Evidence, evaluate_acceptance


def test_v11_05_unknown_obligation_still_blocks():
    context = AcceptanceContext("subject:1", "state:1", "verify:1", "bundle:1", frozenset({"ob:1"}))
    evidence = Evidence("ev:1", "ob:2", "subject:1", "state:1", "verify:1", "bundle:1", True)
    assert evaluate_acceptance(context, (evidence,)).decision is AcceptanceDecision.BLOCK
