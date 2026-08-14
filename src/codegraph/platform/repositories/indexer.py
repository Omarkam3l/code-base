"""Incremental indexing support reusing ingestion and Neo4j graph indexer APIs."""

import hashlib
from pathlib import Path
from typing import Any
from codegraph.ingestion.ingestor import RepositoryIngestor
from codegraph.graph.indexer import RepositoryGraphIndexer
from codegraph.graph.repository import GraphRepository
from codegraph.platform.repositories.models import RepositoryRecord, RepositoryStatus


class IncrementalIndexer:
    """Performs incremental repository ingestion and indexing by skipping unchanged files."""

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """Compute SHA256 content hash for a file."""
        content = file_path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def index_repository(
        self,
        record: RepositoryRecord,
        graph_repo: GraphRepository | None = None,
        force_reindex: bool = False,
    ) -> tuple[RepositoryRecord, dict[str, Any]]:
        """Perform incremental indexing on the target repository."""
        root = Path(record.path)
        if not root.exists():
            record.status = RepositoryStatus.ERROR
            return record, {"status": "error", "message": f"Path non-existent: {root}"}

        record.status = RepositoryStatus.INDEXING

        ingestor = RepositoryIngestor(root=root)
        domain_repo = ingestor.ingest()

        current_hashes: dict[str, str] = {}
        changed_files: list[str] = []

        for pf in domain_repo.files:
            abs_path = root / pf.path
            if abs_path.exists():
                h = self.compute_file_hash(abs_path)
                current_hashes[pf.path] = h
                if force_reindex or record.file_hashes.get(pf.path) != h:
                    changed_files.append(pf.path)

        sources = {f.path: (root / f.path).read_text(encoding="utf-8") for f in domain_repo.files if (root / f.path).exists()}

        if graph_repo:
            graph_indexer = RepositoryGraphIndexer(graph_repo=graph_repo)
            graph_indexer.index(domain_repo, source_code_map=sources)

        record.file_hashes = current_hashes
        record.status = RepositoryStatus.READY

        summary = {
            "total_files": len(domain_repo.files),
            "changed_files_indexed": len(changed_files),
            "skipped_files": len(domain_repo.files) - len(changed_files),
            "status": "success",
        }
        return record, summary
