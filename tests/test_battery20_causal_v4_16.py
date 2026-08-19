from oma.commit import AcceptanceSnapshot,CommitState,CommitToken
from oma.sqlite_commit import DurableCommitDecision,SQLiteTerminalStore

def _objects():
 s=AcceptanceSnapshot('snap','sub','state','policy','obl','evid','ledger',1,1,'root')
 t=CommitToken('tok','snap','sub',1)
 c=CommitState('sub','state','policy','obl','evid','ledger',1,1,policy_bundle_root='root')
 return s,t,c

def test_private_prevalidated_path_can_commit_without_authoritative_registries(tmp_path):
 s,t,c=_objects(); store=SQLiteTerminalStore(tmp_path/'oma.db')
 result=store._commit_prevalidated(s,t,c,terminal_commit_id='terminal')
 assert result.decision is DurableCommitDecision.COMMITTED
 assert store.count()==1
