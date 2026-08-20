from oma.policy import policy_object_root
from oma.retry import RetryDecision, RetryDomain, RetryEvent, RetryEventKind, RetryPolicy, evaluate_retry_domain


def test_v13_13_root_equivalent_retry_container_types_both_execute():
    left = RetryPolicy("retry:v1", 2, 10, frozenset({"verification_failed"}), frozenset({"restart"}))
    right = RetryPolicy("retry:v1", 2, 10, ["verification_failed"], ["restart"])
    domain = RetryDomain("rd:1", "subject:1", "pair:1", "lineage:1", "retry:v1")
    event = RetryEvent("ev:1", 1, RetryEventKind.INITIAL, 1, "run:1", "subject:1", "pair:1", "lineage:1", "rd:1", "retry:v1", "initial", 1)
    assert policy_object_root("retry", left) == policy_object_root("retry", right)
    assert evaluate_retry_domain(left, domain, (event,)).decision is RetryDecision.ALLOW
    assert evaluate_retry_domain(right, domain, (event,)).decision is RetryDecision.ALLOW
