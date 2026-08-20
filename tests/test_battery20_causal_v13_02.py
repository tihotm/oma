from oma.policy import policy_object_root
from oma.scope import ScopePolicy


def test_v13_02_tuple_and_list_scope_paths_have_same_policy_root():
    left = ScopePolicy("scope:v1", ("src",))
    right = ScopePolicy("scope:v1", ["src"])
    assert left != right
    assert policy_object_root("scope", left) == policy_object_root("scope", right)
