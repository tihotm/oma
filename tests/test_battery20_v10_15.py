from oma.authority import AuthorityContext, AuthorityDecision, AuthorityRequest, Capability, evaluate_authority


def test_child_action_escalation_is_blocked():
    context=AuthorityContext("ctx",1,1,frozenset({"issuer"}))
    root=Capability("r","issuer","agent",frozenset({"read"}),frozenset({"subject"}),frozenset({"repo"}),1,0,10)
    child=Capability("c","agent","worker",frozenset({"delete"}),frozenset({"subject"}),frozenset({"repo"}),1,0,9,"r")
    request=AuthorityRequest("worker","delete","subject","repo","c")
    assert evaluate_authority(context,(root,child),request).decision is AuthorityDecision.BLOCK
