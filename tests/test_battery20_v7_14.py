from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.retry_ledger import SQLiteRetryLedger, RetryLedgerDecision


def test_duplicate_event_id_across_domains_conflicts(tmp_path):
    ledger=SQLiteRetryLedger(tmp_path/"oma.db")
    p=RetryPolicy("p",2,10,frozenset({"retry"}),frozenset({"recover"}))
    d1=RetryDomain("d1","s1","pair1","line1","p")
    d2=RetryDomain("d2","s2","pair2","line2","p")
    e1=RetryEvent("shared",1,RetryEventKind.INITIAL,1,"r1","s1","pair1","line1","d1","p","initial",0)
    e2=RetryEvent("shared",1,RetryEventKind.INITIAL,1,"r2","s2","pair2","line2","d2","p","initial",0)
    assert ledger.initialize(p,d1,e1).decision is RetryLedgerDecision.WRITTEN
    assert ledger.initialize(p,d2,e2).decision is RetryLedgerDecision.CONFLICT
