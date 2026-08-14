"""Parameterized Cypher queries for multi-hop graph traversal and intelligence analysis."""

QUERY_MULTI_HOP_PATHS = """
MATCH (source {id: $source_id})
MATCH (target {id: $target_id})
MATCH p = shortestPath((source)-[r:CALLS|IMPORTS|INHERITS*1..8]->(target))
RETURN p, nodes(p) as path_nodes, relationships(p) as path_rels, length(p) as depth
LIMIT $max_paths
"""

QUERY_ALL_PATHS_BETWEEN = """
MATCH (source {id: $source_id})
MATCH (target {id: $target_id})
MATCH p = (source)-[r:CALLS|IMPORTS|INHERITS*1..4]->(target)
RETURN p, nodes(p) as path_nodes, relationships(p) as path_rels, length(p) as depth
LIMIT $max_paths
"""

QUERY_CALL_TRACE_FORWARD = """
MATCH (start {id: $start_id})
MATCH p = (start)-[r:CALLS*1..4]->(target)
RETURN p, nodes(p) as path_nodes, relationships(p) as path_rels, length(p) as depth
LIMIT $max_paths
"""

QUERY_REVERSE_CALL_TRACE = """
MATCH (target {id: $target_id})
MATCH p = (caller)-[r:CALLS*1..4]->(target)
RETURN p, nodes(p) as path_nodes, relationships(p) as path_rels, length(p) as depth
LIMIT $max_paths
"""

QUERY_IMPACT_DEPENDENTS = """
MATCH (target {id: $target_id})
MATCH p = (dependent)-[r:CALLS|IMPORTS|INHERITS*1..4]->(target)
RETURN dependent, labels(dependent) as dependent_labels, type(r[0]) as rel_type, length(p) as distance
LIMIT $max_nodes
"""

QUERY_TYPED_DEPENDENCIES = """
MATCH (n {id: $entity_id})
OPTIONAL MATCH (n)-[r_out:CALLS|IMPORTS|INHERITS]->(out_node)
OPTIONAL MATCH (in_node)-[r_in:CALLS|IMPORTS|INHERITS]->(n)
RETURN out_node, type(r_out) as out_rel, labels(out_node) as out_labels,
       in_node, type(r_in) as in_rel, labels(in_node) as in_labels
"""

QUERY_ARCHITECTURE_NODES = """
MATCH (repo:Repository {id: $repo_id})-[:CONTAINS]->(f:File)
OPTIONAL MATCH (f)-[:DEFINES]->(m:Module)
OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
OPTIONAL MATCH (m)-[:DEFINES]->(fn:Function)
OPTIONAL MATCH (c)-[:DEFINES]->(meth:Method)
RETURN f, m, c, fn, meth
"""
