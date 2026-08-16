"""Tree-sitter parser abstraction for Python source code."""

from dataclasses import dataclass, field
import tree_sitter
import tree_sitter_python


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Result of parsing source code with PythonParser."""

    tree: tree_sitter.Tree
    source_bytes: bytes
    has_syntax_errors: bool
    syntax_errors: tuple[str, ...] = field(default_factory=tuple)


def byte_offset_to_point(source_bytes: bytes, offset: int) -> tuple[int, int]:
    """Convert a byte offset into a 0-based (row, column) point.

    Reads Point attributes off tree_sitter.Node objects via native calls that
    crash with an access violation on some Windows builds, so locations are
    derived from the source bytes in pure Python instead.
    """
    row = source_bytes.count(b"\n", 0, offset)
    last_newline = source_bytes.rfind(b"\n", 0, offset)
    column = offset - (last_newline + 1)
    return row, column


class PythonParser:
    """Dedicated Tree-sitter parser for Python source code.

    This class handles syntax tree generation and syntax error detection without
    performing any semantic extraction.
    """

    def __init__(self) -> None:
        self._language = tree_sitter.Language(tree_sitter_python.language())
        self._parser = tree_sitter.Parser(self._language)

    def parse(self, source: str | bytes) -> ParseResult:
        """Parse Python source code into a Tree-sitter AST.

        Args:
            source: Source code as string or UTF-8 bytes.

        Returns:
            ParseResult containing the syntax tree, source bytes, and syntax error info.
        """
        if isinstance(source, str):
            source_bytes = source.encode("utf-8")
        else:
            source_bytes = source

        tree = self._parser.parse(source_bytes)
        has_error = tree.root_node.has_error
        syntax_errors: list[str] = []

        if has_error:
            syntax_errors = self._collect_syntax_errors(tree.root_node, source_bytes)

        return ParseResult(
            tree=tree,
            source_bytes=source_bytes,
            has_syntax_errors=has_error,
            syntax_errors=tuple(syntax_errors),
        )

    def _collect_syntax_errors(
        self, node: tree_sitter.Node, source_bytes: bytes
    ) -> list[str]:
        """Collect error messages from syntax tree error nodes."""
        errors: list[str] = []

        def _walk(n: tree_sitter.Node) -> None:
            if n.is_error or n.type == "ERROR":
                snippet = n.text.decode("utf-8", errors="replace").strip() if n.text else ""
                row, column = byte_offset_to_point(source_bytes, n.start_byte)
                msg = f"Syntax error at line {row}, column {column}"
                if snippet:
                    msg += f": '{snippet}'"
                errors.append(msg)
            elif n.is_missing:
                row, column = byte_offset_to_point(source_bytes, n.start_byte)
                errors.append(
                    f"Missing expected syntax element at line {row}, column {column}"
                )
            else:
                for child in n.children:
                    if child.has_error:
                        _walk(child)

        _walk(node)
        return errors
