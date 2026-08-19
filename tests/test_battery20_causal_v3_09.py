from oma.obligation import ObligationDecision, ObligationManifest, ObligationSpec, evaluate_obligation_manifest


def test_09_obligation_strength_downgrade_blocks():
    expected = ObligationManifest("set", (ObligationSpec("o1", "req", 2),))
    presented = ObligationManifest("set", (ObligationSpec("o1", "req", 1),))
    result = evaluate_obligation_manifest(expected, presented, acceptance_required_obligations=frozenset({"o1"}))
    assert result.decision is ObligationDecision.BLOCK
    assert "obligation_downgrade:o1" in result.reasons
