from oma.retry import RetryDecision,RetryDomain,RetryEvent,RetryEventKind,RetryPolicy,evaluate_retry_domain

def test_retry_sequence_gap_blocks():
 p=RetryPolicy('rp',3,10,frozenset({'failed'}),frozenset({'recover'})); d=RetryDomain('rd','s','pair','lin','rp')
 e1=RetryEvent('e1',1,RetryEventKind.INITIAL,1,'r','s','pair','lin','rd','rp','initial',0)
 e2=RetryEvent('e2',3,RetryEventKind.RETRY,2,'r','s','pair','lin','rd','rp','failed',0)
 assert evaluate_retry_domain(p,d,(e1,e2)).decision is RetryDecision.BLOCK
