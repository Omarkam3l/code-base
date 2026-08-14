"""Neo4j Repository layer for schema management, batched upserts, and read queries."""

from typing import Any, Sequence
from neo4j import Driver, GraphDatabase

from codegraph.graph.models import (
    ClassNode,
    FileNode,
    FunctionNode,
    GraphNode,
    GraphRelationship,
    MethodNode,
    ModuleNode,
    RepositoryNode,
)
from codegraph.graph.queries import (
    QUERY_FIND_CALLEES,
    QUERY_FIND_CALLERS,
    QUERY_FIND_CLASS,
    QUERY_FIND_DEPENDENTS,
    QUERY_FIND_FUNCTION,
    QUERY_FIND_IMPORTS,
    QUERY_FIND_INHERITANCE_TREE,
    QUERY_GET_REPOSITORY_STRUCTURE,
    UPSERT_CLASSES,
    UPSERT_FILES,
    UPSERT_FUNCTIONS,
    UPSERT_METHODS,
    UPSERT_MODULES,
    UPSERT_REPOSITORIES,
    make_upsert_relationship_query,
)
from codegraph.graph.schema import SCHEMA_CONSTRAINTS, SCHEMA_INDEXES


class GraphRepository:
    """Manages Neo4j database operations, schema creation, batch upserts, and validation queries."""

    def __init__(
        self,
        uri: str | None = None,
        auth: tuple[str, str] | None = None,
        database: str | None = None,
        driver: Driver | None = None,
    ) -> None:
        if driver is not None:
            self._driver = driver
        elif uri and auth:
            self._driver = GraphDatabase.driver(uri, auth=auth)
        else:
            raise ValueError("Must provide either an active Neo4j driver or (uri, auth) credentials.")

        self.database = database

    def close(self) -> None:
        """Close Neo4j driver connection."""
        if self._driver:
            self._driver.close()

    def __enter__(self) -> "GraphRepository":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def create_schema(self) -> None:
        """Create uniqueness constraints and indexes in Neo4j."""
        with self._driver.session(database=self.database) as session:
            for constraint_query in SCHEMA_CONSTRAINTS:
                session.run(constraint_query)
            for index_query in SCHEMA_INDEXES:
                session.run(index_query)

    def upsert_mapping(
        self,
        repo_node: RepositoryNode,
        file_nodes: Sequence[FileNode],
        module_nodes: Sequence[ModuleNode],
        class_nodes: Sequence[ClassNode],
        function_nodes: Sequence[FunctionNode],
        method_nodes: Sequence[MethodNode],
        relationships: Sequence[GraphRelationship],
    ) -> None:
        """Perform batched upsert of all nodes and relationships in a single or batched session."""
        with self._driver.session(database=self.database) as session:
            # 1. Upsert Repository Node
            session.run(UPSERT_REPOSITORIES, batch=[repo_node.to_properties()])

            # 2. Batched File Nodes
            if file_nodes:
                session.run(UPSERT_FILES, batch=[n.to_properties() for n in file_nodes])

            # 3. Batched Module Nodes
            if module_nodes:
                session.run(UPSERT_MODULES, batch=[n.to_properties() for n in module_nodes])

            # 4. Batched Class Nodes
            if class_nodes:
                session.run(UPSERT_CLASSES, batch=[n.to_properties() for n in class_nodes])

            # 5. Batched Function Nodes
            if function_nodes:
                session.run(UPSERT_FUNCTIONS, batch=[n.to_properties() for n in function_nodes])

            # 6. Batched Method Nodes
            if method_nodes:
                session.run(UPSERT_METHODS, batch=[n.to_properties() for n in method_nodes])

            # 7. Batched Relationships grouped by type
            rels_by_type: dict[str, list[dict[str, Any]]] = {}
            for rel in relationships:
                rels_by_type.setdefault(rel.relationship_type, []).append(
                    {
                        "source_id": rel.source_id,
                        "target_id": rel.target_id,
                        **rel.properties,
                    }
                )

            for rel_type, batch in rels_by_type.items():
                query = make_upsert_relationship_query(rel_type)
                session.run(query, batch=batch)

    def get_repository_structure(self, repository_id: str) -> list[dict[str, Any]]:
        """Query repository structure (Files, Modules, Classes, Functions)."""
        with self._driver.session(database=self.database) as session:
            result = session.run(QUERY_GET_REPOSITORY_STRUCTURE, repo_id=repository_id)
            return [record.data() for record in result]

    def find_class(self, qualified_name: str) -> dict[str, Any] | None:
        """Find class node properties by qualified name."""
        with self._driver.session(database=self.database) as session:
            result = session.run(QUERY_FIND_CLASS, qualified_name=qualified_name)
            record = result.single()
            return record["c"] if record else None

    def find_function(self, qualified_name: str) -> dict[str, Any] | None:
        """Find function or method node properties by qualified name."""
        with self._driver.session(database=self.database) as session:
            result = session.run(QUERY_FIND_FUNCTION, qualified_name=qualified_name)
            record = result.single()
            return record["f"] if record else None

    def find_callers(self, entity_id: str) -> list[dict[str, Any]]:
        """Find entities calling target entity_id."""
        with self._driver.session(database=self.database) as session:
            result = session.run(QUERY_FIND_CALLERS, entity_id=entity_id)
            return [
                {
                    "caller": record["caller"],
                    "labels": record["caller_labels"],
                }
                for record in result
            ]

    def find_callees(self, entity_id: str) -> list[dict[str, Any]]:
        """Find entities called by entity_id."""
        with self._driver.session(database=self.database) as session:
            result = session.run(QUERY_FIND_CALLEES, entity_id=entity_id)
            return [
                {
                    "target": record["target"],
                    "labels": record["target_labels"],
                }
                for record in result
            ]

    def find_imports(self, file_id: str) -> list[dict[str, Any]]:
        """Find files imported by file_id."""
        with self._driver.session(database=self.database) as session:
            result = session.run(QUERY_FIND_IMPORTS, file_id=file_id)
            return [record["target"] for record in result]

    def find_dependents(self, file_id: str) -> list[dict[str, Any]]:
        """Find files that import file_id."""
        with self._driver.session(database=self.database) as session:
            result = session.run(QUERY_FIND_DEPENDENTS, file_id=file_id)
            return [record["source"] for record in result]

    def find_inheritance_tree(self, class_id: str) -> list[dict[str, Any]]:
        """Find inheritance path for class_id."""
        with self._driver.session(database=self.database) as session:
            result = session.run(QUERY_FIND_INHERITANCE_TREE, class_id=class_id)
            return [record.data() for record in result]
