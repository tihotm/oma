from oma.authority import AuthorityContext, AuthorityDecision, AuthorityRequest, Capability, evaluate_authority


def test_boolean_epoch_is_accepted_as_one():
    context=AuthorityContext("ctx",True,1,frozenset({"issuer"}))
    capability=Capability("cap","issuer","agent",frozenset({"read"}),frozenset({"subject"}),frozenset({"repo"}),1,0,10)
    request=AuthorityRequest("agent","read","subject","repo","cap")
    assert evaluate_authority(context,(capability,),request).decision is AuthorityDecision.ALLOW
