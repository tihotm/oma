from oma.commit import AcceptanceSnapshot,CommitToken
from oma.sqlite_commit import SQLiteTerminalStore

def test_direct_internal_insert_can_persist_without_validation(tmp_path):
 store=SQLiteTerminalStore(tmp_path/'oma.db')
 s=AcceptanceSnapshot('snap','sub','state','policy','obl','evid','ledger',1,1,'root'); t=CommitToken('tok','snap','sub',1)
 conn=store._connect()
 try:
  conn.execute('BEGIN IMMEDIATE'); store._insert_terminal(conn,s,t,'terminal'); conn.commit()
 finally:
  conn.close()
 assert store.count()==1
