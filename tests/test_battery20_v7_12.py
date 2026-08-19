from oma.retry import RetryDomain, RetryEvent, RetryEventKind, RetryPolicy
from oma.retry_ledger import SQLiteRetryLedger, RetryLedgerDecision


def test_distinct_recovery_reason_sets_can_share_persisted_policy_digest(tmp_path):
    ledger=SQLiteRetryLedger(tmp_path/"oma.db")
    p1=RetryPolicy("p",2,10,frozenset({"retry"}),frozenset({"a","b"}))
    p2=RetryPolicy("p",2,10,frozenset({"retry"}),frozenset({"a\nb"}))
    d=RetryDomain("d","s","pair","line","p")
    e=RetryEvent("e1",1,RetryEventKind.INITIAL,1,"run","s","pair","line","d","p","initial",0)
    assert ledger.initialize(p1,d,e).decision is RetryLedgerDecision.WRITTEN
    assert ledger.get(p2,d)==(e,)
