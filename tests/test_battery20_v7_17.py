from oma.durability import RecoveryDecision, TerminalTransaction, TransactionPhase, validate_transaction


def test_integer_one_is_accepted_as_true_effect_flag():
    tx=TerminalTransaction("t","s",1,"tok","c",phase=TransactionPhase.TOKEN_CONSUMED,token_consumed=1)
    assert validate_transaction(tx).decision is RecoveryDecision.RECOVER
