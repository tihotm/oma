from oma.authority import AuthorityContext
from oma.policy import policy_object_root


def test_v13_03_frozenset_and_list_trusted_issuers_have_same_policy_root():
    left = AuthorityContext("authority:v1", 1, 1, frozenset({"root"}))
    right = AuthorityContext("authority:v1", 1, 1, ["root"])
    assert left != right
    assert policy_object_root("authority", left) == policy_object_root("authority", right)
