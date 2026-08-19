from oma.authority import AuthorityContext, AuthorityDecision, AuthorityRequest, Capability, evaluate_authority


def test_numeric_issuer_identity_is_accepted():
    context=AuthorityContext("ctx",1,1,frozenset({1}))
    capability=Capability("cap",1,"agent",frozenset({"read"}),frozenset({"subject"}),frozenset({"repo"}),1,0,10)
    request=AuthorityRequest("agent","read","subject","repo","cap")
    assert evaluate_authority(context,(capability,),request).decision is AuthorityDecision.ALLOW
