from oma.obligation import ObligationDecision, ObligationManifest, ObligationSpec, evaluate_obligation_manifest


def test_10_acceptance_denominator_omission_blocks():
    manifest = ObligationManifest("set", (ObligationSpec("o1", "req1", 1), ObligationSpec("o2", "req2", 1)))
    result = evaluate_obligation_manifest(manifest, manifest, acceptance_required_obligations=frozenset({"o1"}))
    assert result.decision is ObligationDecision.BLOCK
    assert "acceptance_denominator_missing:o2" in result.reasons
