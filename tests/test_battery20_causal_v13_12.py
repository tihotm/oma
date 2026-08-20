from oma.authority import AuthorityContext, AuthorityDecision, AuthorityRequest, Capability, evaluate_authority
from oma.policy import policy_object_root


def test_v13_12_root_equivalent_authority_container_types_both_execute():
    left = AuthorityContext("authority:v1", 1, 1, frozenset({"root"}))
    right = AuthorityContext("authority:v1", 1, 1, ["root"])
    cap = Capability("cap:1", "root", "agent", frozenset({"commit"}), frozenset({"subject:1"}), frozenset({"repo"}), 1, 0, 10)
    req = AuthorityRequest("agent", "commit", "subject:1", "repo", "cap:1")
    assert policy_object_root("authority", left) == policy_object_root("authority", right)
    assert evaluate_authority(left, (cap,), req).decision is AuthorityDecision.ALLOW
    assert evaluate_authority(right, (cap,), req).decision is AuthorityDecision.ALLOW
