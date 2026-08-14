"""Graph Mapper for converting Phase 1 domain entities to Graph models and resolving relationships."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import tree_sitter
import tree_sitter_python

from codegraph.domain.entities import Class, Function, Import, PythonFile, Repository
from codegraph.graph.models import (
    ClassNode,
    FileNode,
    FunctionNode,
    GraphRelationship,
    MethodNode,
    ModuleNode,
    RepositoryNode,
    make_class_id,
    make_file_id,
    make_function_id,
    make_method_id,
    make_module_id,
    make_repository_id,
)
from codegraph.ingestion.parser import PythonParser


@dataclass
class ResolutionReport:
    """Report summarizing resolved and unresolved structural relationships."""

    resolved_imports_count: int = 0
    unresolved_imports: list[dict[str, Any]] = field(default_factory=list)
    resolved_inherits_count: int = 0
    unresolved_base_classes: list[dict[str, Any]] = field(default_factory=list)
    resolved_calls_count: int = 0
    unresolved_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class GraphMapping:
    """Complete graph projection of an ingested repository."""

    repository_node: RepositoryNode
    file_nodes: tuple[FileNode, ...]
    module_nodes: tuple[ModuleNode, ...]
    class_nodes: tuple[ClassNode, ...]
    function_nodes: tuple[FunctionNode, ...]
    method_nodes: tuple[MethodNode, ...]
    relationships: tuple[GraphRelationship, ...]
    resolution_report: ResolutionReport


class GraphMapper:
    """Maps Phase 1 Repository domain model into Graph Nodes and Relationships."""

    def __init__(self, parser: PythonParser | None = None) -> None:
        self.parser = parser or PythonParser()

    def map_repository(
        self,
        repository: Repository,
        source_code_map: dict[str, str | bytes] | None = None,
    ) -> GraphMapping:
        """Map a Repository domain object to graph nodes and relationships.

        Args:
            repository: Phase 1 Repository domain entity.
            source_code_map: Optional dict mapping file relative path -> source code string or bytes.
                If provided, used for Tree-sitter AST call and inheritance extraction.

        Returns:
            GraphMapping containing all nodes, relationships, and resolution statistics.
        """
        repo_id = make_repository_id(repository.root_path)
        repo_name = Path(repository.root_path).name or "repository"
        repo_node = RepositoryNode(
            id=repo_id,
            labels=("Repository",),
            name=repo_name,
            root_path=repository.root_path,
        )

        file_nodes: list[FileNode] = []
        module_nodes: list[ModuleNode] = []
        class_nodes: list[ClassNode] = []
        function_nodes: list[FunctionNode] = []
        method_nodes: list[MethodNode] = []
        relationships: list[GraphRelationship] = []

        resolution_report = ResolutionReport()

        # Indexes for fast resolution lookup
        module_to_file_id: dict[str, str] = {}
        qname_to_class_id: dict[str, str] = {}
        qname_to_func_id: dict[str, str] = {}
        qname_to_method_id: dict[str, str] = {}

        # 1. Map Nodes and Primary Ownership Relationships (CONTAINS, DEFINES)
        for py_file in repository.files:
            file_id = make_file_id(py_file.path)
            f_node = FileNode(
                id=file_id,
                labels=("File",),
                path=py_file.path,
                language="python",
                module_name=py_file.module_name,
            )
            file_nodes.append(f_node)
            relationships.append(
                GraphRelationship(
                    source_id=repo_id,
                    relationship_type="CONTAINS",
                    target_id=file_id,
                )
            )

            mod_id = make_module_id(py_file.module_name)
            m_node = ModuleNode(
                id=mod_id,
                labels=("Module",),
                name=py_file.module_name,
            )
            module_nodes.append(m_node)
            module_to_file_id[py_file.module_name] = file_id

            relationships.append(
                GraphRelationship(
                    source_id=file_id,
                    relationship_type="DEFINES",
                    target_id=mod_id,
                )
            )

            # Map Classes & Methods
            for cls in py_file.classes:
                qname = self._make_qname(py_file.module_name, cls.name)
                c_id = make_class_id(py_file.module_name, cls.name)
                c_node = ClassNode(
                    id=c_id,
                    labels=("Class",),
                    name=cls.name,
                    qualified_name=qname,
                    file_path=py_file.path,
                    start_line=cls.location.start_line,
                    start_column=cls.location.start_column,
                    end_line=cls.location.end_line,
                    end_column=cls.location.end_column,
                    docstring=cls.docstring,
                )
                class_nodes.append(c_node)
                qname_to_class_id[qname] = c_id
                qname_to_class_id[cls.name] = c_id  # Also index by short name for fallback

                relationships.append(
                    GraphRelationship(
                        source_id=mod_id,
                        relationship_type="DEFINES",
                        target_id=c_id,
                    )
                )

                for meth in cls.methods:
                    m_qname = self._make_qname(py_file.module_name, f"{cls.name}.{meth.name}")
                    meth_id = make_method_id(py_file.module_name, cls.name, meth.name)
                    meth_node = MethodNode(
                        id=meth_id,
                        labels=("Method",),
                        name=meth.name,
                        qualified_name=m_qname,
                        file_path=py_file.path,
                        start_line=meth.location.start_line,
                        start_column=meth.location.start_column,
                        end_line=meth.location.end_line,
                        end_column=meth.location.end_column,
                        return_annotation=meth.return_annotation,
                        docstring=meth.docstring,
                    )
                    method_nodes.append(meth_node)
                    qname_to_method_id[m_qname] = meth_id

                    relationships.append(
                        GraphRelationship(
                            source_id=c_id,
                            relationship_type="DEFINES",
                            target_id=meth_id,
                        )
                    )

            # Map Top-Level Functions
            for fn in py_file.functions:
                fn_qname = self._make_qname(py_file.module_name, fn.name)
                fn_id = make_function_id(py_file.module_name, fn.name)
                fn_node = FunctionNode(
                    id=fn_id,
                    labels=("Function",),
                    name=fn.name,
                    qualified_name=fn_qname,
                    file_path=py_file.path,
                    start_line=fn.location.start_line,
                    start_column=fn.location.start_column,
                    end_line=fn.location.end_line,
                    end_column=fn.location.end_column,
                    return_annotation=fn.return_annotation,
                    docstring=fn.docstring,
                )
                function_nodes.append(fn_node)
                qname_to_func_id[fn_qname] = fn_id
                qname_to_func_id[fn.name] = fn_id

                relationships.append(
                    GraphRelationship(
                        source_id=mod_id,
                        relationship_type="DEFINES",
                        target_id=fn_id,
                    )
                )

        # 2. Resolve IMPORTS Relationships (File -> IMPORTS -> File)
        self._resolve_imports(
            repository=repository,
            module_to_file_id=module_to_file_id,
            relationships=relationships,
            report=resolution_report,
        )

        # 3. Resolve INHERITS & CALLS Relationships (via AST if source code available)
        if source_code_map:
            self._resolve_ast_relationships(
                repository=repository,
                source_code_map=source_code_map,
                module_to_file_id=module_to_file_id,
                qname_to_class_id=qname_to_class_id,
                qname_to_func_id=qname_to_func_id,
                qname_to_method_id=qname_to_method_id,
                relationships=relationships,
                report=resolution_report,
            )

        # Sort all collections deterministically
        file_nodes.sort(key=lambda n: n.id)
        module_nodes.sort(key=lambda n: n.id)
        class_nodes.sort(key=lambda n: n.id)
        function_nodes.sort(key=lambda n: n.id)
        method_nodes.sort(key=lambda n: n.id)
        relationships.sort(key=lambda r: (r.source_id, r.relationship_type, r.target_id))

        return GraphMapping(
            repository_node=repo_node,
            file_nodes=tuple(file_nodes),
            module_nodes=tuple(module_nodes),
            class_nodes=tuple(class_nodes),
            function_nodes=tuple(function_nodes),
            method_nodes=tuple(method_nodes),
            relationships=tuple(relationships),
            resolution_report=resolution_report,
        )

    def _resolve_imports(
        self,
        repository: Repository,
        module_to_file_id: dict[str, str],
        relationships: list[GraphRelationship],
        report: ResolutionReport,
    ) -> None:
        """Resolve import statements to File -> IMPORTS -> File relationships."""
        seen_import_edges: set[tuple[str, str]] = set()

        for py_file in repository.files:
            source_file_id = make_file_id(py_file.path)

            for imp in py_file.imports:
                target_module = self._resolve_target_module_name(py_file.module_name, imp)
                target_file_id = module_to_file_id.get(target_module) if target_module else None

                if target_file_id and target_file_id != source_file_id:
                    edge_key = (source_file_id, target_file_id)
                    if edge_key not in seen_import_edges:
                        seen_import_edges.add(edge_key)
                        relationships.append(
                            GraphRelationship(
                                source_id=source_file_id,
                                relationship_type="IMPORTS",
                                target_id=target_file_id,
                            )
                        )
                        report.resolved_imports_count += 1
                else:
                    report.unresolved_imports.append(
                        {
                            "file": py_file.path,
                            "import_module": imp.module,
                            "import_name": imp.name,
                            "reason": "external_or_unresolved",
                        }
                    )

    def _resolve_target_module_name(self, current_module: str, imp: Import) -> str | None:
        """Resolve import target module string."""
        if not imp.is_relative:
            if imp.module:
                return imp.module
            if imp.name:
                return imp.name
            return None

        # Relative import resolution
        parts = current_module.split(".") if current_module else []
        level = imp.level
        if level > len(parts):
            base_parts = []
        else:
            base_parts = parts[: len(parts) - level]

        if imp.module:
            base_parts.append(imp.module)
        return ".".join(base_parts) if base_parts else None

    def _resolve_ast_relationships(
        self,
        repository: Repository,
        source_code_map: dict[str, str | bytes],
        module_to_file_id: dict[str, str],
        qname_to_class_id: dict[str, str],
        qname_to_func_id: dict[str, str],
        qname_to_method_id: dict[str, str],
        relationships: list[GraphRelationship],
        report: ResolutionReport,
    ) -> None:
        """Extract and resolve INHERITS and CALLS using Tree-sitter AST traversal."""
        seen_inherits: set[tuple[str, str]] = set()
        seen_calls: set[tuple[str, str]] = set()

        for py_file in repository.files:
            source = source_code_map.get(py_file.path)
            if not source:
                continue

            parse_res = self.parser.parse(source)
            if parse_res.has_syntax_errors and not parse_res.tree.root_node:
                continue

            root = parse_res.tree.root_node
            
            # Map of imported symbol name -> full qualified name or target module
            symbol_imports: dict[str, str] = {}
            for imp in py_file.imports:
                target_mod = self._resolve_target_module_name(py_file.module_name, imp)
                if target_mod:
                    local_name = imp.alias or imp.name or imp.module
                    if local_name:
                        if imp.name and imp.name != "*":
                            symbol_imports[local_name] = f"{target_mod}.{imp.name}"
                        else:
                            symbol_imports[local_name] = target_mod

            # Walk top-level statements for Class and Function definitions
            for child in root.children:
                if child.type == "class_definition":
                    self._process_class_ast(
                        node=child,
                        py_file=py_file,
                        symbol_imports=symbol_imports,
                        qname_to_class_id=qname_to_class_id,
                        qname_to_func_id=qname_to_func_id,
                        qname_to_method_id=qname_to_method_id,
                        relationships=relationships,
                        seen_inherits=seen_inherits,
                        seen_calls=seen_calls,
                        report=report,
                    )
                elif child.type in ("function_definition", "async_function_definition"):
                    fn_name = child.child_by_field_name("name")
                    if fn_name:
                        caller_id = make_function_id(py_file.module_name, fn_name.text.decode("utf-8"))
                        self._process_calls_in_node(
                            caller_id=caller_id,
                            caller_class=None,
                            node=child,
                            py_file=py_file,
                            symbol_imports=symbol_imports,
                            qname_to_class_id=qname_to_class_id,
                            qname_to_func_id=qname_to_func_id,
                            qname_to_method_id=qname_to_method_id,
                            relationships=relationships,
                            seen_calls=seen_calls,
                            report=report,
                        )
                elif child.type == "decorated_definition":
                    for sub in child.children:
                        if sub.type == "class_definition":
                            self._process_class_ast(
                                node=sub,
                                py_file=py_file,
                                symbol_imports=symbol_imports,
                                qname_to_class_id=qname_to_class_id,
                                qname_to_func_id=qname_to_func_id,
                                qname_to_method_id=qname_to_method_id,
                                relationships=relationships,
                                seen_inherits=seen_inherits,
                                seen_calls=seen_calls,
                                report=report,
                            )
                        elif sub.type in ("function_definition", "async_function_definition"):
                            fn_name = sub.child_by_field_name("name")
                            if fn_name:
                                caller_id = make_function_id(py_file.module_name, fn_name.text.decode("utf-8"))
                                self._process_calls_in_node(
                                    caller_id=caller_id,
                                    caller_class=None,
                                    node=sub,
                                    py_file=py_file,
                                    symbol_imports=symbol_imports,
                                    qname_to_class_id=qname_to_class_id,
                                    qname_to_func_id=qname_to_func_id,
                                    qname_to_method_id=qname_to_method_id,
                                    relationships=relationships,
                                    seen_calls=seen_calls,
                                    report=report,
                                )

    def _process_class_ast(
        self,
        node: tree_sitter.Node,
        py_file: PythonFile,
        symbol_imports: dict[str, str],
        qname_to_class_id: dict[str, str],
        qname_to_func_id: dict[str, str],
        qname_to_method_id: dict[str, str],
        relationships: list[GraphRelationship],
        seen_inherits: set[tuple[str, str]],
        seen_calls: set[tuple[str, str]],
        report: ResolutionReport,
    ) -> None:
        """Process class inheritance and methods in AST."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        class_name = name_node.text.decode("utf-8")
        sub_class_id = make_class_id(py_file.module_name, class_name)

        # 1. Base classes (INHERITS)
        superclasses = node.child_by_field_name("superclasses")
        if superclasses:
            for base_child in superclasses.children:
                if base_child.type in ("(", ")", ","):
                    continue
                base_expr = base_child.text.decode("utf-8")
                base_class_id = self._resolve_class_ref(
                    base_expr=base_expr,
                    current_module=py_file.module_name,
                    symbol_imports=symbol_imports,
                    qname_to_class_id=qname_to_class_id,
                )
                if base_class_id and base_class_id != sub_class_id:
                    edge_key = (sub_class_id, base_class_id)
                    if edge_key not in seen_inherits:
                        seen_inherits.add(edge_key)
                        relationships.append(
                            GraphRelationship(
                                source_id=sub_class_id,
                                relationship_type="INHERITS",
                                target_id=base_class_id,
                            )
                        )
                        report.resolved_inherits_count += 1
                else:
                    report.unresolved_base_classes.append(
                        {
                            "class": sub_class_id,
                            "base": base_expr,
                            "reason": "unresolved_external_base",
                        }
                    )

        # 2. Methods (CALLS)
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type in ("function_definition", "async_function_definition"):
                    meth_name_node = child.child_by_field_name("name")
                    if meth_name_node:
                        meth_name = meth_name_node.text.decode("utf-8")
                        caller_id = make_method_id(py_file.module_name, class_name, meth_name)
                        self._process_calls_in_node(
                            caller_id=caller_id,
                            caller_class=class_name,
                            node=child,
                            py_file=py_file,
                            symbol_imports=symbol_imports,
                            qname_to_class_id=qname_to_class_id,
                            qname_to_func_id=qname_to_func_id,
                            qname_to_method_id=qname_to_method_id,
                            relationships=relationships,
                            seen_calls=seen_calls,
                            report=report,
                        )

    def _resolve_class_ref(
        self,
        base_expr: str,
        current_module: str,
        symbol_imports: dict[str, str],
        qname_to_class_id: dict[str, str],
    ) -> str | None:
        """Resolve a base class expression string to a target Class ID."""
        # 1. Local in same module
        same_mod_qname = self._make_qname(current_module, base_expr)
        if same_mod_qname in qname_to_class_id:
            return qname_to_class_id[same_mod_qname]

        # 2. Imported symbol
        if base_expr in symbol_imports:
            imported_qname = symbol_imports[base_expr]
            if imported_qname in qname_to_class_id:
                return qname_to_class_id[imported_qname]

        # 3. Global lookup
        if base_expr in qname_to_class_id:
            return qname_to_class_id[base_expr]

        return None

    def _process_calls_in_node(
        self,
        caller_id: str,
        caller_class: str | None,
        node: tree_sitter.Node,
        py_file: PythonFile,
        symbol_imports: dict[str, str],
        qname_to_class_id: dict[str, str],
        qname_to_func_id: dict[str, str],
        qname_to_method_id: dict[str, str],
        relationships: list[GraphRelationship],
        seen_calls: set[tuple[str, str]],
        report: ResolutionReport,
    ) -> None:
        """Traverse AST node for call expressions and resolve target entities."""
        def _walk(n: tree_sitter.Node) -> None:
            if n.type == "call":
                fn_expr_node = n.child_by_field_name("function")
                if fn_expr_node:
                    call_str = fn_expr_node.text.decode("utf-8").strip()
                    target_id = self._resolve_call_target(
                        call_str=call_str,
                        caller_class=caller_class,
                        current_module=py_file.module_name,
                        symbol_imports=symbol_imports,
                        qname_to_class_id=qname_to_class_id,
                        qname_to_func_id=qname_to_func_id,
                        qname_to_method_id=qname_to_method_id,
                    )
                    if target_id and target_id != caller_id:
                        edge_key = (caller_id, target_id)
                        if edge_key not in seen_calls:
                            seen_calls.add(edge_key)
                            relationships.append(
                                GraphRelationship(
                                    source_id=caller_id,
                                    relationship_type="CALLS",
                                    target_id=target_id,
                                )
                            )
                            report.resolved_calls_count += 1
                    else:
                        report.unresolved_calls.append(
                            {
                                "caller": caller_id,
                                "expression": call_str,
                                "reason": "unresolved_or_external_call",
                            }
                        )

            for child in n.children:
                _walk(child)

        body = node.child_by_field_name("body")
        if body:
            _walk(body)

    def _resolve_call_target(
        self,
        call_str: str,
        caller_class: str | None,
        current_module: str,
        symbol_imports: dict[str, str],
        qname_to_class_id: dict[str, str],
        qname_to_func_id: dict[str, str],
        qname_to_method_id: dict[str, str],
    ) -> str | None:
        """Conservatively resolve call expression string to target entity ID."""
        # 1. self.method_name()
        if call_str.startswith("self.") and caller_class:
            m_name = call_str[5:]
            m_qname = self._make_qname(current_module, f"{caller_class}.{m_name}")
            if m_qname in qname_to_method_id:
                return qname_to_method_id[m_qname]

        # 2. Local top-level function in same module
        local_fn_qname = self._make_qname(current_module, call_str)
        if local_fn_qname in qname_to_func_id:
            return qname_to_func_id[local_fn_qname]

        # 3. Class method call: `Class.method()` or `imported_module.Class.method()`
        if "." in call_str:
            parts = call_str.split(".")
            obj_name = parts[0]
            meth_name = parts[-1]

            # Check if obj_name is imported
            if obj_name in symbol_imports:
                imported_target = symbol_imports[obj_name]
                # Target could be class or module
                target_qname = f"{imported_target}.{meth_name}"
                if target_qname in qname_to_method_id:
                    return qname_to_method_id[target_qname]
                if target_qname in qname_to_func_id:
                    return qname_to_func_id[target_qname]

            # Local Class.method in same module
            local_meth_qname = self._make_qname(current_module, call_str)
            if local_meth_qname in qname_to_method_id:
                return qname_to_method_id[local_meth_qname]

        # 4. Imported top-level function or class constructor
        if call_str in symbol_imports:
            imported_qname = symbol_imports[call_str]
            if imported_qname in qname_to_func_id:
                return qname_to_func_id[imported_qname]
            if imported_qname in qname_to_class_id:
                return qname_to_class_id[imported_qname]

        # 5. Global fallback
        if call_str in qname_to_func_id:
            return qname_to_func_id[call_str]
        if call_str in qname_to_class_id:
            return qname_to_class_id[call_str]

        return None

    def _make_qname(self, module_name: str, symbol_name: str) -> str:
        """Format qualified name."""
        if not module_name or module_name in ("__init__", "__root__"):
            return symbol_name
        return f"{module_name}.{symbol_name}"
