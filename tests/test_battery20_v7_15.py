from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.retry_ledger import SQLiteRetryLedger, RetryLedgerDecision


def test_colliding_policy_can_append_reason_not_authorized_by_original_policy(tmp_path):
    ledger=SQLiteRetryLedger(tmp_path/"oma.db")
    p1=RetryPolicy("p",2,10,frozenset({"a","b"}),frozenset({"recover"}))
    p2=RetryPolicy("p",2,10,frozenset({"a\nb"}),frozenset({"recover"}))
    d=RetryDomain("d","s","pair","line","p")
    e1=RetryEvent("e1",1,RetryEventKind.INITIAL,1,"r1","s","pair","line","d","p","initial",0)
    e2=RetryEvent("e2",2,RetryEventKind.RETRY,2,"r2","s","pair","line","d","p","a\nb",0)
    assert ledger.initialize(p1,d,e1).decision is RetryLedgerDecision.WRITTEN
    assert ledger.append(p2,d,e2).decision is RetryLedgerDecision.WRITTEN
    assert ledger.get(p1,d)==(e1,e2)
