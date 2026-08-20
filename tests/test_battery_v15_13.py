from oma.retry import RetryDecision, RetryDomain, RetryEvent, RetryEventKind, RetryPolicy, evaluate_retry_domain


def test_numeric_authorized_retry_reason_is_currently_allowed():
    p=RetryPolicy('p',2,10,frozenset({7}),frozenset({'recover'})); d=RetryDomain('d','s','pair','line','p')
    e1=RetryEvent('e1',1,RetryEventKind.INITIAL,1,'run1','s','pair','line','d','p','initial',0)
    e2=RetryEvent('e2',2,RetryEventKind.RETRY,2,'run2','s','pair','line','d','p',7,0)
    assert evaluate_retry_domain(p,d,(e1,e2)).decision is RetryDecision.ALLOW
