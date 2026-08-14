"""Integration tests for live Neo4j persistence, idempotency, and read query API."""

import os
from pathlib import Path
import pytest
from neo4j import GraphDatabase

from codegraph.ingestion.ingestor import RepositoryIngestor
from codegraph.graph.repository import GraphRepository
from codegraph.graph.indexer import RepositoryGraphIndexer
from codegraph.graph.models import make_file_id, make_method_id

# Live Neo4j instance credentials
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://d63ecd97.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "d63ecd97")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "yd8PYJDFKLibHwuYapLR092yToTjDpiQe4fM7JPzJiU")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "d63ecd97")


@pytest.fixture
def live_graph_repo() -> GraphRepository:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    repo = GraphRepository(driver=driver, database=NEO4J_DATABASE)
    yield repo
    repo.close()


def test_neo4j_connectivity(live_graph_repo: GraphRepository) -> None:
    live_graph_repo.create_schema()


def test_sample_project_graph_indexing_and_queries(live_graph_repo: GraphRepository) -> None:
    sample_dir = Path("examples/sample_project")
    assert sample_dir.exists()

    # 1. Ingest sample project with Phase 1
    ingestor = RepositoryIngestor(root=sample_dir)
    domain_repo = ingestor.ingest()
    assert len(domain_repo.files) == 3

    # Load source code for AST resolution
    sources: dict[str, str] = {}
    for f in domain_repo.files:
        sources[f.path] = (sample_dir / f.path).read_text(encoding="utf-8")

    # 2. Index into Neo4j with Phase 2
    graph_indexer = RepositoryGraphIndexer(graph_repo=live_graph_repo)
    result = graph_indexer.index(domain_repo, source_code_map=sources)

    assert result.file_count == 3
    assert result.class_count >= 2
    assert result.relationship_count > 0

    # 3. Test Read API Queries
    repo_id = result.mapping.repository_node.id
    structure = live_graph_repo.get_repository_structure(repo_id)
    assert len(structure) > 0

    # Find User class
    user_cls = live_graph_repo.find_class("models.User")
    assert user_cls is not None
    assert user_cls["name"] == "User"

    # Find imports from services.py
    services_file_id = make_file_id("services.py")
    imports = live_graph_repo.find_imports(services_file_id)
    imported_paths = [f["path"] for f in imports]
    assert "models.py" in imported_paths


def test_idempotency(live_graph_repo: GraphRepository) -> None:
    sample_dir = Path("examples/sample_project")
    ingestor = RepositoryIngestor(root=sample_dir)
    domain_repo = ingestor.ingest()

    sources: dict[str, str] = {}
    for f in domain_repo.files:
        sources[f.path] = (sample_dir / f.path).read_text(encoding="utf-8")

    graph_indexer = RepositoryGraphIndexer(graph_repo=live_graph_repo)

    # First indexing run
    res1 = graph_indexer.index(domain_repo, source_code_map=sources)

    # Query total node and relationship count in database
    with live_graph_repo._driver.session(database=NEO4J_DATABASE) as session:
        node_count_1 = session.run("MATCH (n) RETURN count(n) as cnt").single()["cnt"]
        rel_count_1 = session.run("MATCH ()-[r]->() RETURN count(r) as cnt").single()["cnt"]

    # Second indexing run (re-indexing identical repository)
    res2 = graph_indexer.index(domain_repo, source_code_map=sources)

    with live_graph_repo._driver.session(database=NEO4J_DATABASE) as session:
        node_count_2 = session.run("MATCH (n) RETURN count(n) as cnt").single()["cnt"]
        rel_count_2 = session.run("MATCH ()-[r]->() RETURN count(r) as cnt").single()["cnt"]

    # Hard requirement: Node count and relationship count must remain identical
    assert node_count_1 == node_count_2
    assert rel_count_1 == rel_count_2
