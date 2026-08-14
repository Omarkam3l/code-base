"""Repository Graph Indexer for orchestrating Phase 2 Code Knowledge Graph indexing."""

from dataclasses import dataclass
from typing import Mapping

from codegraph.domain.entities import Repository
from codegraph.graph.mapper import GraphMapper, GraphMapping
from codegraph.graph.repository import GraphRepository


@dataclass(frozen=True, slots=True)
class IndexingResult:
    """Result of repository graph indexing operation."""

    mapping: GraphMapping
    file_count: int
    class_count: int
    function_count: int
    method_count: int
    relationship_count: int


class RepositoryGraphIndexer:
    """Orchestrates indexing of a Phase 1 Repository into Neo4j Code Knowledge Graph."""

    def __init__(
        self,
        graph_repo: GraphRepository,
        mapper: GraphMapper | None = None,
    ) -> None:
        self.graph_repo = graph_repo
        self.mapper = mapper or GraphMapper()

    def index(
        self,
        repository: Repository,
        source_code_map: dict[str, str | bytes] | None = None,
    ) -> IndexingResult:
        """Index a Phase 1 Repository into Neo4j.

        Args:
            repository: Ingested Phase 1 Repository domain object.
            source_code_map: Optional dict mapping relative file path -> source code string/bytes.

        Returns:
            IndexingResult containing the graph mapping details and counts.
        """
        # Ensure Neo4j schema constraints and indexes exist
        self.graph_repo.create_schema()

        # Map domain model to graph nodes and relationships
        mapping = self.mapper.map_repository(repository, source_code_map=source_code_map)

        # Upsert mapping into Neo4j using batched queries
        self.graph_repo.upsert_mapping(
            repo_node=mapping.repository_node,
            file_nodes=mapping.file_nodes,
            module_nodes=mapping.module_nodes,
            class_nodes=mapping.class_nodes,
            function_nodes=mapping.function_nodes,
            method_nodes=mapping.method_nodes,
            relationships=mapping.relationships,
        )

        return IndexingResult(
            mapping=mapping,
            file_count=len(mapping.file_nodes),
            class_count=len(mapping.class_nodes),
            function_count=len(mapping.function_nodes),
            method_count=len(mapping.method_nodes),
            relationship_count=len(mapping.relationships),
        )
