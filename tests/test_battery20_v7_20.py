from oma.durability import TerminalTransaction, observable_effect_ids, recover_transaction


def test_recovery_preserves_observable_effect_ids():
    tx=TerminalTransaction("t","s",1,"tok","c")
    before=observable_effect_ids(tx)
    recovered=recover_transaction(tx).transaction
    assert recovered is not None
    assert observable_effect_ids(recovered)==before
