import pytest

from oma.durability import (
    RecoveryDecision,
    TerminalTransaction,
    TransactionPhase,
    advance_transaction,
    observable_effect_ids,
    recover_transaction,
    validate_transaction,
)


def tx(**overrides):
    values = dict(
        terminal_transaction_id="txn:1",
        subject_id="subject:1",
        terminal_epoch=2,
        token_id="token:1",
        terminal_commit_id="commit:1",
    )
    values.update(overrides)
    return TerminalTransaction(**values)


def at_phase(phase):
    values = {
        TransactionPhase.PREPARED: {},
        TransactionPhase.TOKEN_CONSUMED: dict(token_consumed=True),
        TransactionPhase.TERMINAL_RECORDED: dict(token_consumed=True, terminal_recorded=True),
        TransactionPhase.EFFECTS_RECORDED: dict(token_consumed=True, terminal_recorded=True, ledger_recorded=True, provenance_recorded=True),
        TransactionPhase.COMMITTED: dict(token_consumed=True, terminal_recorded=True, ledger_recorded=True, provenance_recorded=True),
    }[phase]
    return tx(phase=phase, **values)


@pytest.mark.parametrize("phase", list(TransactionPhase))
def test_valid_phase_shapes_are_accepted(phase):
    result = validate_transaction(at_phase(phase))
    expected = RecoveryDecision.COMMITTED if phase is TransactionPhase.COMMITTED else RecoveryDecision.RECOVER
    assert result.decision is expected


@pytest.mark.parametrize("phase", [
    TransactionPhase.PREPARED,
    TransactionPhase.TOKEN_CONSUMED,
    TransactionPhase.TERMINAL_RECORDED,
    TransactionPhase.EFFECTS_RECORDED,
])
def test_recovery_completes_every_partial_phase(phase):
    result = recover_transaction(at_phase(phase))
    assert result.decision is RecoveryDecision.COMMITTED
    assert result.transaction.phase is TransactionPhase.COMMITTED


def test_recovery_is_idempotent():
    once = recover_transaction(at_phase(TransactionPhase.TOKEN_CONSUMED))
    twice = recover_transaction(once.transaction)
    assert twice == once


@pytest.mark.parametrize("bad", [
    dict(phase=TransactionPhase.PREPARED, token_consumed=True),
    dict(phase=TransactionPhase.TOKEN_CONSUMED, token_consumed=False),
    dict(phase=TransactionPhase.TERMINAL_RECORDED, token_consumed=True, terminal_recorded=False),
    dict(phase=TransactionPhase.EFFECTS_RECORDED, token_consumed=True, terminal_recorded=True, ledger_recorded=True, provenance_recorded=False),
    dict(phase=TransactionPhase.COMMITTED, token_consumed=True, terminal_recorded=True, ledger_recorded=False, provenance_recorded=True),
])
def test_partial_inconsistent_states_block(bad):
    assert validate_transaction(tx(**bad)).decision is RecoveryDecision.BLOCK


def test_phase_rollback_blocks():
    current = at_phase(TransactionPhase.TERMINAL_RECORDED)
    assert advance_transaction(current, TransactionPhase.TOKEN_CONSUMED).decision is RecoveryDecision.BLOCK


def test_phase_skip_blocks():
    assert advance_transaction(at_phase(TransactionPhase.PREPARED), TransactionPhase.TERMINAL_RECORDED).decision is RecoveryDecision.BLOCK


def test_same_phase_is_idempotent():
    current = at_phase(TransactionPhase.TERMINAL_RECORDED)
    result = advance_transaction(current, TransactionPhase.TERMINAL_RECORDED)
    assert result.transaction == current


@pytest.mark.parametrize("field", [
    "terminal_transaction_id", "subject_id", "token_id", "terminal_commit_id"
])
def test_missing_identity_blocks(field):
    assert validate_transaction(tx(**{field: ""})).decision is RecoveryDecision.BLOCK


def test_negative_terminal_epoch_blocks():
    assert validate_transaction(tx(terminal_epoch=-1)).decision is RecoveryDecision.BLOCK


def test_observable_effect_ids_are_deterministic():
    assert observable_effect_ids(tx()) == observable_effect_ids(tx())


def test_different_transactions_have_disjoint_effect_ids():
    assert observable_effect_ids(tx()).isdisjoint(
        observable_effect_ids(tx(terminal_transaction_id="txn:2"))
    )


def test_recovery_preserves_transaction_identity_and_epoch():
    original = at_phase(TransactionPhase.PREPARED)
    recovered = recover_transaction(original).transaction
    assert recovered.terminal_transaction_id == original.terminal_transaction_id
    assert recovered.subject_id == original.subject_id
    assert recovered.terminal_epoch == original.terminal_epoch
    assert recovered.token_id == original.token_id
    assert recovered.terminal_commit_id == original.terminal_commit_id
