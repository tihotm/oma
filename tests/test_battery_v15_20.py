import sqlite3
import pytest
from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.retry_ledger import SQLiteRetryLedger


def test_retry_ledger_corrupt_kind_currently_raises_value_error(tmp_path):
    path=tmp_path/'r.db'; p=RetryPolicy('p',3,10,frozenset({'ok'}),frozenset({'recover'})); d=RetryDomain('d','s','pair','line','p')
    e=RetryEvent('e1',1,RetryEventKind.INITIAL,1,'run1','s','pair','line','d','p','initial',0)
    ledger=SQLiteRetryLedger(path); ledger.initialize(p,d,e)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE retry_events SET kind='BOGUS' WHERE event_id='e1'")
        conn.commit()
    with pytest.raises(ValueError):
        ledger.get(p,d)
