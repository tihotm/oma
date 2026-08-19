from oma.authority import AuthorityContext, AuthorityDecision, AuthorityRequest, Capability, evaluate_authority


def test_numeric_action_identity_is_accepted():
    context=AuthorityContext("ctx",1,1,frozenset({"issuer"}))
    capability=Capability("cap","issuer","agent",frozenset({1}),frozenset({"subject"}),frozenset({"repo"}),1,0,10)
    request=AuthorityRequest("agent",1,"subject","repo","cap")
    assert evaluate_authority(context,(capability,),request).decision is AuthorityDecision.ALLOW
