"""Rollback manager for isolated temporary workspace snapshots."""

import shutil
import tempfile
from pathlib import Path


class RollbackManager:
    """Manages workspace snapshots, restoration, and cleanup to ensure failed iterations are reversible."""

    def __init__(self) -> None:
        self._snapshots: list[Path] = []

    def snapshot_workspace(self, workspace_path: str | Path) -> Path:
        """Create a temporary directory snapshot of current workspace files."""
        ws_path = Path(workspace_path)
        snapshot_dir = Path(tempfile.mkdtemp(prefix="codegraph_snapshot_"))

        # Copy all workspace contents to snapshot directory
        for item in ws_path.iterdir():
            dest = snapshot_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        self._snapshots.append(snapshot_dir)
        return snapshot_dir

    def restore_snapshot(self, workspace_path: str | Path, snapshot_path: str | Path) -> None:
        """Restore workspace files from snapshot directory."""
        ws_path = Path(workspace_path)
        snap_path = Path(snapshot_path)

        if not snap_path.exists():
            return

        # Clean workspace directory contents
        for item in ws_path.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

        # Restore contents from snapshot
        for item in snap_path.iterdir():
            dest = ws_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    def discard_iteration(self, workspace_path: str | Path, snapshot_path: str | Path) -> None:
        """Restore workspace snapshot and clean up temporary snapshot directory."""
        snap_path = Path(snapshot_path)
        self.restore_snapshot(workspace_path, snap_path)

        if snap_path.exists():
            shutil.rmtree(snap_path, ignore_errors=True)

        if snap_path in self._snapshots:
            self._snapshots.remove(snap_path)

    def cleanup_all_snapshots(self) -> None:
        """Clean up any remaining temporary snapshot directories."""
        for snap in list(self._snapshots):
            if snap.exists():
                shutil.rmtree(snap, ignore_errors=True)
        self._snapshots.clear()
