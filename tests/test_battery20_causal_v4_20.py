from oma.commit import AcceptanceSnapshot,CommitState,CommitToken
from oma.sqlite_commit import DurableCommitDecision,SQLiteTerminalStore

def test_subject_terminal_epoch_unique(tmp_path):
 store=SQLiteTerminalStore(tmp_path/'oma.db')
 s=AcceptanceSnapshot('snap','sub','state','policy','obl','evid','ledger',1,1,'root'); c=CommitState('sub','state','policy','obl','evid','ledger',1,1,policy_bundle_root='root')
 t1=CommitToken('tok1','snap','sub',1); t2=CommitToken('tok2','snap','sub',1)
 assert store._commit_prevalidated(s,t1,c,terminal_commit_id='t1').decision is DurableCommitDecision.COMMITTED
 assert store._commit_prevalidated(s,t2,c,terminal_commit_id='t2').decision is DurableCommitDecision.CONFLICT
