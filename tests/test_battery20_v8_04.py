from oma.obligation import ObligationDecision, ObligationManifest, ObligationSpec, evaluate_obligation_manifest


def test_newline_obligation_identifier_is_accepted():
    m=ObligationManifest("set",(ObligationSpec("o\n1","req",1),))
    result=evaluate_obligation_manifest(m,m,acceptance_required_obligations=frozenset({"o\n1"}))
    assert result.decision is ObligationDecision.ALLOW
