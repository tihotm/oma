from oma.terminal import TerminalDecision, TerminalPolicy, evaluate_terminal_barrier
from oma.validation import ValidationDecision, ValidationObservation


def test_newline_prerequisite_id_is_accepted_when_observation_matches():
    p=TerminalPolicy("tp",frozenset({"n\n1"}),frozenset({"COMMIT"}))
    obs=(ValidationObservation("n\n1",ValidationDecision.ACCEPT,"root"),)
    assert evaluate_terminal_barrier(p,obs,requested_action="COMMIT").decision is TerminalDecision.ALLOW
