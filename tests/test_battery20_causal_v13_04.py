from oma.policy import policy_object_root
from oma.retry import RetryPolicy


def test_v13_04_frozenset_and_list_retry_reasons_have_same_policy_root():
    left = RetryPolicy("retry:v1", 2, 10, frozenset({"verification_failed"}), frozenset({"restart"}))
    right = RetryPolicy("retry:v1", 2, 10, ["verification_failed"], ["restart"])
    assert left != right
    assert policy_object_root("retry", left) == policy_object_root("retry", right)
