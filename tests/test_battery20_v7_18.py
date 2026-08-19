from oma.durability import TerminalTransaction, observable_effect_ids


def test_distinct_transactions_can_share_terminal_effect_id_by_delimiter_collision():
    a=TerminalTransaction("a","s1",1,"tok1","b:terminal:c")
    b=TerminalTransaction("a:terminal:b","s2",1,"tok2","c")
    assert observable_effect_ids(a) & observable_effect_ids(b) == {"a:terminal:b:terminal:c"}
