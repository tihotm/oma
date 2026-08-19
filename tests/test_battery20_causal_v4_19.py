from oma.commit import AcceptanceSnapshot,CommitState,CommitToken
from oma.sqlite_commit import DurableCommitDecision,SQLiteTerminalStore

def _triple(subject,epoch,token):
 s=AcceptanceSnapshot('snap-'+subject,subject,'state','policy','obl','evid','ledger',1,epoch,'root')
 t=CommitToken(token,s.acceptance_snapshot_id,subject,epoch)
 c=CommitState(subject,'state','policy','obl','evid','ledger',1,epoch,policy_bundle_root='root')
 return s,t,c

def test_durable_token_id_unique_across_subjects(tmp_path):
 store=SQLiteTerminalStore(tmp_path/'oma.db'); s1,t1,c1=_triple('a',1,'same-token'); s2,t2,c2=_triple('b',2,'same-token')
 assert store._commit_prevalidated(s1,t1,c1,terminal_commit_id='t1').decision is DurableCommitDecision.COMMITTED
 assert store._commit_prevalidated(s2,t2,c2,terminal_commit_id='t2').decision is DurableCommitDecision.CONFLICT
