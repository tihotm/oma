from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.retry_ledger import SQLiteRetryLedger, RetryLedgerDecision


def test_newline_event_id_is_accepted_on_initialization(tmp_path):
    ledger=SQLiteRetryLedger(tmp_path/"oma.db")
    p=RetryPolicy("p",2,10,frozenset({"retry"}),frozenset({"recover"}))
    d=RetryDomain("d","s","pair","line","p")
    e=RetryEvent("e\n1",1,RetryEventKind.INITIAL,1,"run","s","pair","line","d","p","initial",0)
    assert ledger.initialize(p,d,e).decision is RetryLedgerDecision.WRITTEN
