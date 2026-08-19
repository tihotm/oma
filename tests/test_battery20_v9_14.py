from oma.terminal import TerminalDecision, TerminalPolicy, evaluate_terminal_barrier
from oma.validation import ValidationDecision, ValidationObservation


def test_unexpected_terminal_observation_is_blocked():
    p=TerminalPolicy("tp",frozenset({"n"}),frozenset({"COMMIT"}))
    obs=(ValidationObservation("n",ValidationDecision.ACCEPT,"r"),ValidationObservation("x",ValidationDecision.ACCEPT,"x"))
    assert evaluate_terminal_barrier(p,obs,requested_action="COMMIT").decision is TerminalDecision.BLOCK
