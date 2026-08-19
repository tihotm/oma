from oma.terminal import TerminalDecision, TerminalPolicy, evaluate_terminal_barrier
from oma.validation import ValidationDecision, ValidationObservation


def test_newline_evidence_root_is_accepted():
    p=TerminalPolicy("tp",frozenset({"n"}),frozenset({"COMMIT"}))
    obs=(ValidationObservation("n",ValidationDecision.ACCEPT,"root\nshift"),)
    assert evaluate_terminal_barrier(p,obs,requested_action="COMMIT").decision is TerminalDecision.ALLOW
