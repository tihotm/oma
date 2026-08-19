from oma.retry import (
    RetryDecision, RetryDomain, RetryEvent, RetryEventKind, RetryPolicy,
    evaluate_retry_domain,
)


def _policy(max_attempts=3, max_cost=10):
    return RetryPolicy("rp", max_attempts, max_cost, frozenset({"failed"}), frozenset({"recover"}))


def _domain():
    return RetryDomain("rd", "s", "pair", "lin", "rp")


def _event(event_id, sequence, kind, attempt, reason, cost=0, run="r"):
    return RetryEvent(event_id, sequence, kind, attempt, run, "s", "pair", "lin", "rd", "rp", reason, cost)


def test_06_empty_retry_history_currently_allows():
    result = evaluate_retry_domain(_policy(), _domain(), ())
    assert result.decision is RetryDecision.ALLOW
