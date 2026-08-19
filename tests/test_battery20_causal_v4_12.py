from oma.terminal import TerminalDecision,canonical_terminal_policy,evaluate_terminal_barrier
from oma.validation import ValidationDecision,ValidationObservation

def test_unexpected_terminal_prerequisite_blocks():
 p=canonical_terminal_policy('term'); obs=[ValidationObservation(i,ValidationDecision.ACCEPT,'r') for i in p.required_node_ids]; obs.append(ValidationObservation('extra',ValidationDecision.ACCEPT,'r'))
 assert evaluate_terminal_barrier(p,tuple(obs),requested_action='COMMIT').decision is TerminalDecision.BLOCK
