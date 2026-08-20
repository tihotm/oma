from dataclasses import replace
from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.retry_ledger import SQLiteRetryLedger


def test_retry_ledger_wrong_domain_binding_returns_none(tmp_path):
    p=RetryPolicy('p',3,10,frozenset({'ok'}),frozenset({'recover'})); d=RetryDomain('d','s','pair','line','p')
    e=RetryEvent('e1',1,RetryEventKind.INITIAL,1,'run1','s','pair','line','d','p','initial',0)
    ledger=SQLiteRetryLedger(tmp_path/'r.db'); ledger.initialize(p,d,e)
    assert ledger.get(p,replace(d,subject_id='other')) is None
