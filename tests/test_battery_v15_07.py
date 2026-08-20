from oma.retry import RetryDecision, RetryDomain, RetryEvent, RetryEventKind, RetryPolicy, evaluate_retry_domain


def test_bool_cost_limit_is_accepted_as_integer_one():
    policy=RetryPolicy('p',2,True,frozenset({'retry'}),frozenset({'recover'}))
    domain=RetryDomain('d','s','pair','line','p')
    event=RetryEvent('e',1,RetryEventKind.INITIAL,1,'run','s','pair','line','d','p','initial',1)
    out=evaluate_retry_domain(policy,domain,(event,))
    assert out.decision is RetryDecision.ALLOW and out.cumulative_cost == 1
