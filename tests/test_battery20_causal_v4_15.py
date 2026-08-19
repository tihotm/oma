from oma.terminal import TerminalDecision,canonical_terminal_policy,evaluate_terminal_barrier
from oma.validation import ValidationDecision,ValidationObservation

def test_terminal_action_is_bound_into_barrier_root():
 p=canonical_terminal_policy('term'); obs=tuple(ValidationObservation(i,ValidationDecision.ACCEPT,'r') for i in p.required_node_ids)
 done=evaluate_terminal_barrier(p,obs,requested_action='DONE'); commit=evaluate_terminal_barrier(p,obs,requested_action='COMMIT')
 assert done.decision is TerminalDecision.ALLOW and commit.decision is TerminalDecision.ALLOW
 assert done.terminal_barrier_root != commit.terminal_barrier_root
