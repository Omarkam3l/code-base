"""Parameterized Cypher queries for batched upserts and graph validation queries."""

# Node Upserts (UNWIND + MERGE + SET +=)
UPSERT_REPOSITORIES = """
UNWIND $batch AS row
MERGE (n:Repository {id: row.id})
SET n.name = row.name,
    n.root_path = row.root_path
"""

UPSERT_FILES = """
UNWIND $batch AS row
MERGE (n:File {id: row.id})
SET n.path = row.path,
    n.language = row.language,
    n.module_name = row.module_name
"""

UPSERT_MODULES = """
UNWIND $batch AS row
MERGE (n:Module {id: row.id})
SET n.name = row.name
"""

UPSERT_CLASSES = """
UNWIND $batch AS row
MERGE (n:Class {id: row.id})
SET n.name = row.name,
    n.qualified_name = row.qualified_name,
    n.file_path = row.file_path,
    n.start_line = row.start_line,
    n.start_column = row.start_column,
    n.end_line = row.end_line,
    n.end_column = row.end_column,
    n.docstring = row.docstring
"""

UPSERT_FUNCTIONS = """
UNWIND $batch AS row
MERGE (n:Function {id: row.id})
SET n.name = row.name,
    n.qualified_name = row.qualified_name,
    n.file_path = row.file_path,
    n.start_line = row.start_line,
    n.start_column = row.start_column,
    n.end_line = row.end_line,
    n.end_column = row.end_column,
    n.return_annotation = row.return_annotation,
    n.docstring = row.docstring
"""

UPSERT_METHODS = """
UNWIND $batch AS row
MERGE (n:Method {id: row.id})
SET n.name = row.name,
    n.qualified_name = row.qualified_name,
    n.file_path = row.file_path,
    n.start_line = row.start_line,
    n.start_column = row.start_column,
    n.end_line = row.end_line,
    n.end_column = row.end_column,
    n.return_annotation = row.return_annotation,
    n.docstring = row.docstring
"""


# Relationship Upserts
def make_upsert_relationship_query(rel_type: str) -> str:
    """Generate Cypher MERGE query for a specific relationship type."""
    return f"""
    UNWIND $batch AS row
    MATCH (source {{id: row.source_id}})
    MATCH (target {{id: row.target_id}})
    MERGE (source)-[r:{rel_type}]->(target)
    """


# Validation / Read Queries
QUERY_GET_REPOSITORY_STRUCTURE = """
MATCH (r:Repository {id: $repo_id})-[:CONTAINS]->(f:File)
OPTIONAL MATCH (f)-[:DEFINES]->(m:Module)
OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
OPTIONAL MATCH (m)-[:DEFINES]->(fn:Function)
OPTIONAL MATCH (c)-[:DEFINES]->(meth:Method)
RETURN r, f, m, collect(distinct c) as classes, collect(distinct fn) as functions, collect(distinct meth) as methods
"""

QUERY_FIND_CLASS = """
MATCH (c:Class {qualified_name: $qualified_name})
RETURN c
"""

QUERY_FIND_FUNCTION = """
MATCH (f:Function)
WHERE f.qualified_name = $qualified_name
RETURN f
UNION
MATCH (m:Method)
WHERE m.qualified_name = $qualified_name
RETURN m
"""

QUERY_FIND_CALLERS = """
MATCH (caller)-[:CALLS]->(target {id: $entity_id})
RETURN caller, labels(caller) as caller_labels
"""

QUERY_FIND_CALLEES = """
MATCH (caller {id: $entity_id})-[:CALLS]->(target)
RETURN target, labels(target) as target_labels
"""

QUERY_FIND_IMPORTS = """
MATCH (f:File {id: $file_id})-[:IMPORTS]->(target:File)
RETURN target
"""

QUERY_FIND_DEPENDENTS = """
MATCH (source:File)-[:IMPORTS]->(f:File {id: $file_id})
RETURN source
"""

QUERY_FIND_INHERITANCE_TREE = """
MATCH path = (sub:Class)-[:INHERITS*]->(base:Class)
WHERE sub.id = $class_id OR base.id = $class_id
RETURN path
"""
