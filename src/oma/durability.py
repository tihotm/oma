from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum, StrEnum


class TransactionPhase(IntEnum):
    PREPARED = 1
    TOKEN_CONSUMED = 2
    TERMINAL_RECORDED = 3
    EFFECTS_RECORDED = 4
    COMMITTED = 5


class RecoveryDecision(StrEnum):
    RECOVER = "RECOVER"
    COMMITTED = "COMMITTED"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class TerminalTransaction:
    terminal_transaction_id: str
    subject_id: str
    terminal_epoch: int
    token_id: str
    terminal_commit_id: str
    phase: TransactionPhase = TransactionPhase.PREPARED
    token_consumed: bool = False
    terminal_recorded: bool = False
    ledger_recorded: bool = False
    provenance_recorded: bool = False


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    decision: RecoveryDecision
    reasons: tuple[str, ...] = ()
    transaction: TerminalTransaction | None = None


def validate_transaction(tx: TerminalTransaction) -> RecoveryResult:
    if (
        not tx.terminal_transaction_id
        or not tx.subject_id
        or not tx.token_id
        or not tx.terminal_commit_id
        or tx.terminal_epoch < 0
    ):
        return RecoveryResult(RecoveryDecision.BLOCK, ("invalid_terminal_transaction",), tx)

    expected = {
        TransactionPhase.PREPARED: (False, False, False, False),
        TransactionPhase.TOKEN_CONSUMED: (True, False, False, False),
        TransactionPhase.TERMINAL_RECORDED: (True, True, False, False),
        TransactionPhase.EFFECTS_RECORDED: (True, True, True, True),
        TransactionPhase.COMMITTED: (True, True, True, True),
    }[tx.phase]
    actual = (
        tx.token_consumed,
        tx.terminal_recorded,
        tx.ledger_recorded,
        tx.provenance_recorded,
    )
    if actual != expected:
        return RecoveryResult(
            RecoveryDecision.BLOCK,
            (f"phase_effect_mismatch:{tx.phase.name}",),
            tx,
        )
    if tx.phase is TransactionPhase.COMMITTED:
        return RecoveryResult(RecoveryDecision.COMMITTED, (), tx)
    return RecoveryResult(RecoveryDecision.RECOVER, (), tx)


def advance_transaction(
    tx: TerminalTransaction,
    target_phase: TransactionPhase,
) -> RecoveryResult:
    current = validate_transaction(tx)
    if current.decision is RecoveryDecision.BLOCK:
        return current
    if target_phase < tx.phase:
        return RecoveryResult(RecoveryDecision.BLOCK, ("transaction_phase_rollback",), tx)
    if target_phase > tx.phase + 1:
        return RecoveryResult(RecoveryDecision.BLOCK, ("transaction_phase_skip",), tx)
    if target_phase == tx.phase:
        return current

    if target_phase is TransactionPhase.TOKEN_CONSUMED:
        next_tx = replace(tx, phase=target_phase, token_consumed=True)
    elif target_phase is TransactionPhase.TERMINAL_RECORDED:
        next_tx = replace(tx, phase=target_phase, terminal_recorded=True)
    elif target_phase is TransactionPhase.EFFECTS_RECORDED:
        next_tx = replace(
            tx,
            phase=target_phase,
            ledger_recorded=True,
            provenance_recorded=True,
        )
    elif target_phase is TransactionPhase.COMMITTED:
        next_tx = replace(tx, phase=target_phase)
    else:
        return RecoveryResult(RecoveryDecision.BLOCK, ("invalid_target_phase",), tx)

    return validate_transaction(next_tx)


def recover_transaction(tx: TerminalTransaction) -> RecoveryResult:
    """Deterministically reconcile one terminal transaction to COMMITTED.

    Re-running recovery on the committed result is idempotent. Inconsistent
    durable states fail closed rather than being silently rewritten.
    """
    current = validate_transaction(tx)
    if current.decision is RecoveryDecision.BLOCK:
        return current
    if current.decision is RecoveryDecision.COMMITTED:
        return current

    working = tx
    while working.phase is not TransactionPhase.COMMITTED:
        result = advance_transaction(working, TransactionPhase(working.phase + 1))
        if result.decision is RecoveryDecision.BLOCK:
            return result
        working = result.transaction
        assert working is not None
    return RecoveryResult(RecoveryDecision.COMMITTED, (), working)


def observable_effect_ids(tx: TerminalTransaction) -> frozenset[str]:
    """Return deterministic IDs for externally observable terminal effects."""
    return frozenset({
        f"{tx.terminal_transaction_id}:terminal:{tx.terminal_commit_id}",
        f"{tx.terminal_transaction_id}:ledger",
        f"{tx.terminal_transaction_id}:provenance",
    })
