"""Neo4j constraints and indexes definition for Code Knowledge Graph."""

SCHEMA_CONSTRAINTS: tuple[str, ...] = (
    "CREATE CONSTRAINT repository_id_unique IF NOT EXISTS FOR (n:Repository) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT file_id_unique IF NOT EXISTS FOR (n:File) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT module_id_unique IF NOT EXISTS FOR (n:Module) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT class_id_unique IF NOT EXISTS FOR (n:Class) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT function_id_unique IF NOT EXISTS FOR (n:Function) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT method_id_unique IF NOT EXISTS FOR (n:Method) REQUIRE n.id IS UNIQUE",
)

SCHEMA_INDEXES: tuple[str, ...] = (
    "CREATE INDEX file_path_idx IF NOT EXISTS FOR (n:File) ON (n.path)",
    "CREATE INDEX module_name_idx IF NOT EXISTS FOR (n:Module) ON (n.name)",
    "CREATE INDEX class_qname_idx IF NOT EXISTS FOR (n:Class) ON (n.qualified_name)",
    "CREATE INDEX function_qname_idx IF NOT EXISTS FOR (n:Function) ON (n.qualified_name)",
    "CREATE INDEX method_qname_idx IF NOT EXISTS FOR (n:Method) ON (n.qualified_name)",
)
