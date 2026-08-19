from oma.terminal import TerminalDecision,canonical_terminal_policy,evaluate_terminal_barrier
from oma.validation import ValidationDecision,ValidationObservation

def test_terminal_stale_dominates_not_done():
 p=canonical_terminal_policy('term'); ids=sorted(p.required_node_ids); obs=[]
 for i in ids:
  d=ValidationDecision.ACCEPT
  if i==ids[0]: d=ValidationDecision.STALE
  elif i==ids[1]: d=ValidationDecision.NOT_DONE
  obs.append(ValidationObservation(i,d,'r'))
 assert evaluate_terminal_barrier(p,tuple(obs),requested_action='COMMIT').decision is TerminalDecision.STALE
