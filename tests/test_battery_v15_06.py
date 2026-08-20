from oma.retry import RetryDecision, RetryDomain, RetryEvent, RetryEventKind, RetryPolicy, evaluate_retry_domain


def test_bool_max_attempts_is_accepted_as_integer_one():
    policy=RetryPolicy('p',True,10,frozenset({'retry'}),frozenset({'recover'}))
    domain=RetryDomain('d','s','pair','line','p')
    event=RetryEvent('e',1,RetryEventKind.INITIAL,1,'run','s','pair','line','d','p','initial',0)
    assert evaluate_retry_domain(policy,domain,(event,)).decision is RetryDecision.ALLOW
