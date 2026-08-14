"""Unit tests for RollbackManager and workspace snapshot restoration."""

import tempfile
from pathlib import Path
from codegraph.repair.rollback import RollbackManager


def test_rollback_manager_snapshot_and_restore() -> None:
    with tempfile.TemporaryDirectory() as tmp_ws:
        ws_path = Path(tmp_ws)
        file1 = ws_path / "test.txt"
        file1.write_text("initial content", encoding="utf-8")

        mgr = RollbackManager()
        snapshot = mgr.snapshot_workspace(ws_path)

        # Modify file in workspace
        file1.write_text("modified broken content", encoding="utf-8")
        assert file1.read_text(encoding="utf-8") == "modified broken content"

        # Restore snapshot
        mgr.restore_snapshot(ws_path, snapshot)
        assert file1.read_text(encoding="utf-8") == "initial content"

        # Cleanup
        mgr.discard_iteration(ws_path, snapshot)
        assert not snapshot.exists()
