from oma.durability import RecoveryDecision, TerminalTransaction, validate_transaction


def test_newline_transaction_identity_is_accepted():
    tx=TerminalTransaction("tx\n1","s",1,"tok","c")
    assert validate_transaction(tx).decision is RecoveryDecision.RECOVER
