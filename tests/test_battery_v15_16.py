from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.retry_ledger import RetryLedgerDecision, SQLiteRetryLedger


def test_blocked_retry_event_remains_in_durable_history(tmp_path):
    p=RetryPolicy('p',3,10,frozenset({'ok'}),frozenset({'recover'})); d=RetryDomain('d','s','pair','line','p')
    initial=RetryEvent('e1',1,RetryEventKind.INITIAL,1,'run1','s','pair','line','d','p','initial',0)
    bad=RetryEvent('e2',2,RetryEventKind.RETRY,2,'run2','s','pair','line','d','p','bad',0)
    ledger=SQLiteRetryLedger(tmp_path/'r.db'); assert ledger.initialize(p,d,initial).decision is RetryLedgerDecision.WRITTEN
    assert ledger.append(p,d,bad).decision is RetryLedgerDecision.BLOCKED
    assert [e.event_id for e in ledger.get(p,d)] == ['e1','e2']
