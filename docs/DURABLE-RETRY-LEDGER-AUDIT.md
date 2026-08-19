# Durable Retry Ledger Audit

Baseline under test: `25eefeea5930148afc3eb0363dae4dc38e2e1053`

## Question

Can a caller omit factual retry/cost history and thereby reopen a terminal ACCEPT path that the complete history would block?

## Adversarial construction

The current retry policy allows at most two execution attempts. The audit constructs a factual history with:

1. INITIAL attempt 1
2. authorized RETRY attempt 2
3. authorized RETRY attempt 3

The complete history must block because attempt 3 exceeds `max_execution_attempts=2`.

The attack then presents only event 1 to the supported composed execution boundary while keeping subject, pair, lineage, policy and durable subject state otherwise unchanged.

If the truncated history reaches durable ACCEPT, then retry history is not authoritative and Item 32 remains causally exploitable at the supported boundary.

## Expected interpretation

- complete history -> `retry_recovery=BLOCK`, zero terminal writes
- truncated caller history -> if `retry_recovery=ACCEPT` and durable global `ACCEPT`, causal failure is confirmed

This PR exists to execute the whole repository suite against the attack. No production retry-ledger fix is included yet; implementation should follow only if CI confirms the causal failure.
