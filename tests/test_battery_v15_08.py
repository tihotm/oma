from oma.retry import RetryDecision, RetryDomain, RetryEvent, RetryEventKind, RetryPolicy, evaluate_retry_domain


def test_bool_sequence_is_accepted_as_sequence_one():
    policy=RetryPolicy('p',2,10,frozenset({'retry'}),frozenset({'recover'}))
    domain=RetryDomain('d','s','pair','line','p')
    event=RetryEvent('e',True,RetryEventKind.INITIAL,1,'run','s','pair','line','d','p','initial',0)
    assert evaluate_retry_domain(policy,domain,(event,)).decision is RetryDecision.ALLOW
