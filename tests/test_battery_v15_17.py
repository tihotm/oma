from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.retry_ledger import RetryLedgerDecision, SQLiteRetryLedger


def test_valid_later_event_does_not_launder_prior_blocked_history(tmp_path):
    p=RetryPolicy('p',4,10,frozenset({'ok'}),frozenset({'recover'})); d=RetryDomain('d','s','pair','line','p')
    e1=RetryEvent('e1',1,RetryEventKind.INITIAL,1,'run1','s','pair','line','d','p','initial',0)
    e2=RetryEvent('e2',2,RetryEventKind.RETRY,2,'run2','s','pair','line','d','p','bad',0)
    e3=RetryEvent('e3',3,RetryEventKind.RETRY,2,'run3','s','pair','line','d','p','ok',0)
    ledger=SQLiteRetryLedger(tmp_path/'r.db'); ledger.initialize(p,d,e1); ledger.append(p,d,e2)
    assert ledger.append(p,d,e3).decision is RetryLedgerDecision.BLOCKED
    assert len(ledger.get(p,d)) == 3
