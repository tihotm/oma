from oma.commit import AcceptanceSnapshot,CommitState,CommitToken
from oma.sqlite_commit import SQLiteTerminalStore

def test_prevalidated_storage_path_persists_terminal_without_closure_proof(tmp_path):
 s=AcceptanceSnapshot('snap','sub','state','policy','obl','evid','ledger',1,1,'root'); t=CommitToken('tok','snap','sub',1); c=CommitState('sub','state','policy','obl','evid','ledger',1,1,policy_bundle_root='root')
 store=SQLiteTerminalStore(tmp_path/'oma.db'); store._commit_prevalidated(s,t,c,terminal_commit_id='terminal')
 r=store.get('terminal')
 assert r is not None
 assert r.validation_graph_id is None and r.terminal_barrier_root is None and r.precommit_closure_digest is None
