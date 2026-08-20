from oma.retry import RetryDecision, RetryDomain, RetryEvent, RetryEventKind, RetryPolicy, evaluate_retry_domain


def test_numeric_run_id_is_currently_allowed():
    p=RetryPolicy('p',2,10,frozenset({'retry'}),frozenset({'recover'})); d=RetryDomain('d','s','pair','line','p')
    e=RetryEvent('e',1,RetryEventKind.INITIAL,1,123,'s','pair','line','d','p','initial',0)
    assert evaluate_retry_domain(p,d,(e,)).decision is RetryDecision.ALLOW
