from oma.retry import RetryDecision, RetryDomain, RetryEvent, RetryEventKind, RetryPolicy, evaluate_retry_domain


def test_bool_attempt_number_is_accepted_as_one():
    policy=RetryPolicy('p',2,10,frozenset({'retry'}),frozenset({'recover'}))
    domain=RetryDomain('d','s','pair','line','p')
    event=RetryEvent('e',1,RetryEventKind.INITIAL,True,'run','s','pair','line','d','p','initial',0)
    assert evaluate_retry_domain(policy,domain,(event,)).decision is RetryDecision.ALLOW
