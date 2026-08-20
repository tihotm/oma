from oma.retry import RetryDecision, RetryDomain, RetryEvent, RetryEventKind, RetryPolicy, evaluate_retry_domain


def test_negative_retry_cost_is_blocked():
    policy=RetryPolicy('p',2,10,frozenset({'retry'}),frozenset({'recover'}))
    domain=RetryDomain('d','s','pair','line','p')
    event=RetryEvent('e',1,RetryEventKind.INITIAL,1,'run','s','pair','line','d','p','initial',-1)
    assert evaluate_retry_domain(policy,domain,(event,)).decision is RetryDecision.BLOCK
