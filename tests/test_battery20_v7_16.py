import pytest
from oma.durability import TerminalTransaction, validate_transaction


def test_unknown_raw_phase_raises_instead_of_fail_closed_block():
    tx=TerminalTransaction("t","s",1,"tok","c",phase=99)
    with pytest.raises(KeyError):
        validate_transaction(tx)
