from oma.terminal import TerminalDecision, TerminalPolicy, evaluate_terminal_barrier
from oma.validation import ValidationDecision, ValidationObservation


def test_newline_terminal_action_is_accepted_when_policy_allows_it():
    p=TerminalPolicy("tp",frozenset({"n"}),frozenset({"COM\nMIT"}))
    obs=(ValidationObservation("n",ValidationDecision.ACCEPT,"root"),)
    assert evaluate_terminal_barrier(p,obs,requested_action="COM\nMIT").decision is TerminalDecision.ALLOW
