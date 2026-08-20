from oma.retry import RetryDecision, RetryDomain, RetryEvent, RetryPolicy, evaluate_retry_domain


def test_string_retry_kind_is_blocked():
    p=RetryPolicy('p',2,10,frozenset({'retry'}),frozenset({'recover'})); d=RetryDomain('d','s','pair','line','p')
    e=RetryEvent('e',1,'INITIAL',1,'run','s','pair','line','d','p','initial',0)
    assert evaluate_retry_domain(p,d,(e,)).decision is RetryDecision.BLOCK
