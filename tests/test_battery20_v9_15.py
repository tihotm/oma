from oma.terminal import TerminalDecision, TerminalPolicy, evaluate_terminal_barrier


def test_missing_terminal_prerequisite_is_not_done():
    p=TerminalPolicy("tp",frozenset({"n"}),frozenset({"COMMIT"}))
    assert evaluate_terminal_barrier(p,(),requested_action="COMMIT").decision is TerminalDecision.NOT_DONE
