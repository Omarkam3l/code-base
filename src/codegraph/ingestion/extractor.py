"""AST Extractor for extracting domain entities from Tree-sitter syntax trees."""

from pathlib import Path
import tree_sitter

from codegraph.domain.entities import (
    Class,
    Function,
    Import,
    Parameter,
    PythonFile,
    SourceLocation,
)
from codegraph.ingestion.parser import ParseResult, byte_offset_to_point


class PythonExtractor:
    """Extracts code entities (Imports, Classes, Functions, Parameters) from Tree-sitter ASTs."""

    def extract(
        self,
        parse_result: ParseResult,
        path: str,
        module_name: str,
    ) -> PythonFile:
        """Extract PythonFile domain entity from a ParseResult.

        Args:
            parse_result: The result returned by PythonParser.parse().
            path: Repository-relative file path (POSIX format).
            module_name: Deterministically computed Python module name.

        Returns:
            Extracted PythonFile domain object.
        """
        source_bytes = parse_result.source_bytes
        tree = parse_result.tree
        root_node = tree.root_node

        imports: list[Import] = []
        classes: list[Class] = []
        functions: list[Function] = []

        self._extract_top_level(
            node=root_node,
            source_bytes=source_bytes,
            imports=imports,
            classes=classes,
            functions=functions,
        )

        # Sort extracted items deterministically
        imports.sort(
            key=lambda i: (
                i.location.start_line if i.location else 0,
                i.location.start_column if i.location else 0,
                i.module or "",
                i.name or "",
            )
        )
        classes.sort(
            key=lambda c: (
                c.location.start_line,
                c.location.start_column,
                c.name,
            )
        )
        functions.sort(
            key=lambda f: (
                f.location.start_line,
                f.location.start_column,
                f.name,
            )
        )

        return PythonFile(
            path=path,
            module_name=module_name,
            imports=tuple(imports),
            classes=tuple(classes),
            functions=tuple(functions),
            has_syntax_errors=parse_result.has_syntax_errors,
            syntax_errors=parse_result.syntax_errors,
        )

    def _extract_top_level(
        self,
        node: tree_sitter.Node,
        source_bytes: bytes,
        imports: list[Import],
        classes: list[Class],
        functions: list[Function],
    ) -> None:
        """Traverse top-level statements and compound top-level blocks."""
        for child in node.children:
            if child.type == "import_statement":
                imports.extend(self._extract_import_statement(child, source_bytes))
            elif child.type == "import_from_statement":
                imports.extend(self._extract_import_from_statement(child, source_bytes))
            elif child.type == "class_definition":
                cls = self._extract_class(child, source_bytes)
                if cls:
                    classes.append(cls)
            elif child.type in ("function_definition", "async_function_definition"):
                fn = self._extract_function(child, source_bytes)
                if fn:
                    functions.append(fn)
            elif child.type == "decorated_definition":
                for sub in child.children:
                    if sub.type == "class_definition":
                        cls = self._extract_class(sub, source_bytes)
                        if cls:
                            classes.append(cls)
                    elif sub.type in ("function_definition", "async_function_definition"):
                        fn = self._extract_function(sub, source_bytes)
                        if fn:
                            functions.append(fn)
            elif child.type in ("if_statement", "try_statement", "with_statement"):
                # Recurse into top-level compound statement blocks
                for sub in child.children:
                    if sub.type in ("block", "consequence", "alternative"):
                        self._extract_top_level(sub, source_bytes, imports, classes, functions)

    def _extract_import_statement(
        self, node: tree_sitter.Node, source_bytes: bytes
    ) -> list[Import]:
        """Extract imports from `import os`, `import os.path`, `import foo, bar as b`."""
        loc = self._get_location(node, source_bytes)
        results: list[Import] = []

        for child in node.children:
            if child.type == "dotted_name":
                mod_name = child.text.decode("utf-8")
                results.append(
                    Import(
                        module=mod_name,
                        name="",
                        alias=None,
                        is_relative=False,
                        level=0,
                        location=loc,
                    )
                )
            elif child.type == "aliased_import":
                # dotted_name as alias
                name_node = child.child_by_field_name("name") or child.children[0]
                alias_node = child.child_by_field_name("alias") or child.children[-1]
                mod_name = name_node.text.decode("utf-8")
                alias_str = alias_node.text.decode("utf-8")
                results.append(
                    Import(
                        module=mod_name,
                        name="",
                        alias=alias_str,
                        is_relative=False,
                        level=0,
                        location=loc,
                    )
                )
        return results

    def _extract_import_from_statement(
        self, node: tree_sitter.Node, source_bytes: bytes
    ) -> list[Import]:
        """Extract imports from `from x import y`, `from .models import User`, `from x import *`."""
        loc = self._get_location(node, source_bytes)
        results: list[Import] = []

        module_str: str | None = None
        is_relative = False
        level = 0

        # Discover module source (dotted_name or relative_import)
        module_node = node.child_by_field_name("module_name")
        if not module_node:
            for child in node.children:
                if child.type in ("dotted_name", "relative_import"):
                    module_node = child
                    break

        if module_node:
            if module_node.type == "relative_import":
                is_relative = True
                text = module_node.text.decode("utf-8")
                dots = len(text) - len(text.lstrip("."))
                level = dots
                mod_part = text[dots:]
                module_str = mod_part if mod_part else None
            else:
                module_str = module_node.text.decode("utf-8")
                is_relative = False
                level = 0

        # Discover imported names (after 'import' keyword)
        import_keyword_found = False
        for child in node.children:
            if child.type == "import":
                import_keyword_found = True
                continue

            if not import_keyword_found:
                continue

            self._process_imported_item(
                node=child,
                module_str=module_str,
                is_relative=is_relative,
                level=level,
                location=loc,
                results=results,
            )

        return results

    def _process_imported_item(
        self,
        node: tree_sitter.Node,
        module_str: str | None,
        is_relative: bool,
        level: int,
        location: SourceLocation,
        results: list[Import],
    ) -> None:
        """Helper to process individual imported items inside a from-import statement."""
        if node.type == "dotted_name" or node.type == "identifier":
            item_name = node.text.decode("utf-8")
            results.append(
                Import(
                    module=module_str,
                    name=item_name,
                    alias=None,
                    is_relative=is_relative,
                    level=level,
                    location=location,
                )
            )
        elif node.type == "aliased_import":
            name_node = node.child_by_field_name("name") or node.children[0]
            alias_node = node.child_by_field_name("alias") or node.children[-1]
            item_name = name_node.text.decode("utf-8")
            alias_str = alias_node.text.decode("utf-8")
            results.append(
                Import(
                    module=module_str,
                    name=item_name,
                    alias=alias_str,
                    is_relative=is_relative,
                    level=level,
                    location=location,
                )
            )
        elif node.type == "wildcard_import" or node.text.decode("utf-8") == "*":
            results.append(
                Import(
                    module=module_str,
                    name="*",
                    alias=None,
                    is_relative=is_relative,
                    level=level,
                    location=location,
                )
            )
        elif node.type in ("parenthesized_import", "import_list"):
            for sub in node.children:
                if sub.type not in ("(", ")", ","):
                    self._process_imported_item(
                        sub, module_str, is_relative, level, location, results
                    )

    def _extract_class(
        self, node: tree_sitter.Node, source_bytes: bytes
    ) -> Class | None:
        """Extract Class domain entity from a class_definition AST node."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        class_name = name_node.text.decode("utf-8")
        loc = self._get_location(node, source_bytes)

        body_node = node.child_by_field_name("body")
        methods: list[Function] = []
        docstring: str | None = None

        if body_node:
            docstring = self._extract_docstring(body_node)
            for child in body_node.children:
                if child.type in ("function_definition", "async_function_definition"):
                    fn = self._extract_function(child, source_bytes)
                    if fn:
                        methods.append(fn)
                elif child.type == "decorated_definition":
                    for sub in child.children:
                        if sub.type in ("function_definition", "async_function_definition"):
                            fn = self._extract_function(sub, source_bytes)
                            if fn:
                                methods.append(fn)

        methods.sort(key=lambda m: (m.location.start_line, m.location.start_column, m.name))

        return Class(
            name=class_name,
            location=loc,
            methods=tuple(methods),
            docstring=docstring,
        )

    def _extract_function(
        self, node: tree_sitter.Node, source_bytes: bytes
    ) -> Function | None:
        """Extract Function domain entity from a function_definition AST node."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        fn_name = name_node.text.decode("utf-8")
        loc = self._get_location(node, source_bytes)
        is_async = node.type == "async_function_definition"

        # Return annotation
        return_annotation: str | None = None
        return_type_node = node.child_by_field_name("return_type")
        if return_type_node:
            return_annotation = return_type_node.text.decode("utf-8").strip()

        # Parameters
        parameters: list[Parameter] = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            parameters = self._extract_parameters(params_node, source_bytes)

        # Docstring
        docstring: str | None = None
        body_node = node.child_by_field_name("body")
        if body_node:
            docstring = self._extract_docstring(body_node)

        return Function(
            name=fn_name,
            location=loc,
            parameters=tuple(parameters),
            return_annotation=return_annotation,
            is_async=is_async,
            docstring=docstring,
        )

    def _extract_parameters(
        self, params_node: tree_sitter.Node, source_bytes: bytes
    ) -> list[Parameter]:
        """Extract parameter list from parameters node with position/keyword classification."""
        parameters: list[Parameter] = []
        current_kind = "POSITIONAL_OR_KEYWORD"

        for child in params_node.children:
            if child.type in ("(", ")", ","):
                continue

            if child.type == "positional_separator":
                # Convert preceding POSITIONAL_OR_KEYWORD parameters to POSITIONAL_ONLY
                parameters = [
                    Parameter(
                        name=p.name,
                        type_annotation=p.type_annotation,
                        default_value=p.default_value,
                        kind="POSITIONAL_ONLY" if p.kind == "POSITIONAL_OR_KEYWORD" else p.kind,
                    )
                    for p in parameters
                ]
                current_kind = "POSITIONAL_OR_KEYWORD"
                continue

            if child.type == "keyword_separator":
                current_kind = "KEYWORD_ONLY"
                continue

            param = self._extract_single_parameter(child, current_kind, source_bytes)
            if param:
                parameters.append(param)
                if param.kind == "VAR_POSITIONAL":
                    current_kind = "KEYWORD_ONLY"

        return parameters

    def _extract_single_parameter(
        self, node: tree_sitter.Node, default_kind: str, source_bytes: bytes
    ) -> Parameter | None:
        """Extract single parameter details from parameter AST node."""
        kind = default_kind
        name = ""
        type_annotation: str | None = None
        default_value: str | None = None

        if node.type == "identifier":
            name = node.text.decode("utf-8")
        elif node.type == "typed_parameter":
            name_node = node.child_by_field_name("name") or node.children[0]
            name = name_node.text.decode("utf-8")
            type_node = node.child_by_field_name("type")
            if type_node:
                type_annotation = type_node.text.decode("utf-8").strip()

            if name_node.type == "list_splat_pattern" or (name.startswith("*") and not name.startswith("**")):
                kind = "VAR_POSITIONAL"
            elif name_node.type == "dictionary_splat_pattern" or name.startswith("**"):
                kind = "VAR_KEYWORD"

        elif node.type == "default_parameter":
            name_node = node.child_by_field_name("name") or node.children[0]
            name = name_node.text.decode("utf-8")
            val_node = node.child_by_field_name("value")
            if val_node:
                default_value = val_node.text.decode("utf-8").strip()

        elif node.type == "typed_default_parameter":
            name_node = node.child_by_field_name("name") or node.children[0]
            name = name_node.text.decode("utf-8")
            type_node = node.child_by_field_name("type")
            if type_node:
                type_annotation = type_node.text.decode("utf-8").strip()
            val_node = node.child_by_field_name("value")
            if val_node:
                default_value = val_node.text.decode("utf-8").strip()

        elif node.type in ("list_splat_pattern", "splat_parameter"):
            name = node.text.decode("utf-8")
            kind = "VAR_POSITIONAL"

        elif node.type in ("dictionary_splat_pattern", "dictionary_splat"):
            name = node.text.decode("utf-8")
            kind = "VAR_KEYWORD"

        else:
            name = node.text.decode("utf-8")

        if not name:
            return None

        return Parameter(
            name=name,
            type_annotation=type_annotation,
            default_value=default_value,
            kind=kind,
        )

    def _extract_docstring(self, body_node: tree_sitter.Node) -> str | None:
        """Extract docstring text if first statement in body is a string expression."""
        for child in body_node.children:
            if child.type == "expression_statement":
                for sub in child.children:
                    if sub.type == "string":
                        raw = sub.text.decode("utf-8")
                        # Strip triple or single quotes
                        for quote in ('"""', "'''", '"', "'"):
                            if raw.startswith(quote) and raw.endswith(quote) and len(raw) >= 2 * len(quote):
                                return raw[len(quote) : -len(quote)].strip()
                        return raw.strip()
            # Stop checking after comments or non-comment statements
            if child.type not in ("comment",):
                break
        return None

    def _get_location(
        self, node: tree_sitter.Node, source_bytes: bytes
    ) -> SourceLocation:
        """Convert Tree-sitter Node coordinates to 0-based SourceLocation.

        Row/column values are derived from byte offsets instead of
        node.start_point/end_point, whose native Point accessors crash with an
        access violation on some Windows builds.
        """
        start_line, start_column = byte_offset_to_point(source_bytes, node.start_byte)
        end_line, end_column = byte_offset_to_point(source_bytes, node.end_byte)
        return SourceLocation(
            start_line=start_line,
            start_column=start_column,
            end_line=end_line,
            end_column=end_column,
        )
