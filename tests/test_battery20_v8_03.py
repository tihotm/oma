from oma.obligation import ObligationDecision, ObligationManifest, ObligationSpec, evaluate_obligation_manifest


def test_boolean_strength_is_accepted_as_integer_strength():
    m=ObligationManifest("set",(ObligationSpec("o","req",True),))
    result=evaluate_obligation_manifest(m,m,acceptance_required_obligations=frozenset({"o"}))
    assert result.decision is ObligationDecision.ALLOW
