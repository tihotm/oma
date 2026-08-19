from oma.obligation import ObligationDecision, ObligationManifest, ObligationSpec, evaluate_obligation_manifest


def test_obligation_strength_mutation_is_blocked():
    expected=ObligationManifest("set",(ObligationSpec("o","req",1),))
    presented=ObligationManifest("set",(ObligationSpec("o","req",2),))
    assert evaluate_obligation_manifest(expected,presented,acceptance_required_obligations=frozenset({"o"})).decision is ObligationDecision.BLOCK
