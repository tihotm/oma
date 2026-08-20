import pytest
from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.retry_ledger import SQLiteRetryLedger


def test_retry_ledger_append_string_kind_currently_raises_attribute_error(tmp_path):
    p=RetryPolicy('p',3,10,frozenset({'ok'}),frozenset({'recover'})); d=RetryDomain('d','s','pair','line','p')
    e1=RetryEvent('e1',1,RetryEventKind.INITIAL,1,'run1','s','pair','line','d','p','initial',0)
    bad=RetryEvent('e2',2,'RETRY',2,'run2','s','pair','line','d','p','ok',0)
    ledger=SQLiteRetryLedger(tmp_path/'r.db'); ledger.initialize(p,d,e1)
    with pytest.raises(AttributeError):
        ledger.append(p,d,bad)
