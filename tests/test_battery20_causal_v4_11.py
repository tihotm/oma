from oma.terminal import TerminalDecision,canonical_terminal_policy,evaluate_terminal_barrier
from oma.validation import ValidationDecision,ValidationObservation

def test_missing_terminal_prerequisite_is_not_done():
 p=canonical_terminal_policy('term'); ids=sorted(p.required_node_ids); obs=tuple(ValidationObservation(i,ValidationDecision.ACCEPT,'r') for i in ids[1:])
 assert evaluate_terminal_barrier(p,obs,requested_action='COMMIT').decision is TerminalDecision.NOT_DONE
