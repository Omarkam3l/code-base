"""Storage interface and file-backed repository implementation for Investigation records."""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import asdict
from codegraph.platform.investigations.models import InvestigationRecord


def _default_investigation_storage_dir() -> Path:
    """Resolve the default investigation storage directory.

    Honors CODEGRAPH_DATA_DIR when set (e.g. for a real deployment). Otherwise
    falls back to a per-user data directory outside the repo, so importing this
    module — or running the test suite, which exercises it via the API and unit
    tests — never writes files into the source tree.
    """
    env_dir = os.environ.get("CODEGRAPH_DATA_DIR")
    if env_dir:
        return Path(env_dir) / "investigations"
    return Path.home() / ".codegraph" / "investigations"


class InvestigationStore(ABC):
    """Abstract persistence interface for investigation records."""

    @abstractmethod
    def save(self, record: InvestigationRecord) -> None:
        """Save investigation record."""
        pass

    @abstractmethod
    def get(self, investigation_id: str) -> InvestigationRecord | None:
        """Get investigation record by ID."""
        pass

    @abstractmethod
    def list_all(self, repository_id: str | None = None) -> list[InvestigationRecord]:
        """List investigation records."""
        pass


class FileInvestigationStore(InvestigationStore):
    """File-backed investigation repository storing records in JSON files."""

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        self.storage_dir = Path(storage_dir) if storage_dir is not None else _default_investigation_storage_dir()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, InvestigationRecord] = {}

    def save(self, record: InvestigationRecord) -> None:
        """Save investigation record to JSON file and memory cache."""
        self._memory_cache[record.investigation_id] = record
        file_path = self.storage_dir / f"{record.investigation_id}.json"
        data = asdict(record)
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get(self, investigation_id: str) -> InvestigationRecord | None:
        """Retrieve investigation record by ID."""
        if investigation_id in self._memory_cache:
            return self._memory_cache[investigation_id]

        file_path = self.storage_dir / f"{investigation_id}.json"
        if not file_path.exists():
            return None

        data = json.loads(file_path.read_text(encoding="utf-8"))
        record = InvestigationRecord(**data)
        self._memory_cache[investigation_id] = record
        return record

    def list_all(self, repository_id: str | None = None) -> list[InvestigationRecord]:
        """List stored investigation records."""
        records: list[InvestigationRecord] = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                rec = InvestigationRecord(**data)
                if repository_id is None or rec.repository_id == repository_id:
                    records.append(rec)
            except Exception:
                continue
        return records
