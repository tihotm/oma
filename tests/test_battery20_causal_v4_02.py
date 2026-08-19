from dataclasses import replace
from tests.test_battery20_causal_v4_01 import _pair
from oma.snapshot import SnapshotDecision, evaluate_snapshot_freshness


def test_snapshot_terminal_epoch_rollback_blocks():
    snapshot, current = _pair()
    result = evaluate_snapshot_freshness(snapshot, replace(current, terminal_epoch=2))
    assert result.decision is SnapshotDecision.BLOCK
