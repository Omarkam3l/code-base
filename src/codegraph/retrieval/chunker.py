"""Code chunker for converting Phase 1 domain entities into searchable CodeChunk objects."""

from typing import Mapping
from codegraph.domain.entities import Class, Function, PythonFile, Repository
from codegraph.graph.models import (
    make_class_id,
    make_function_id,
    make_method_id,
    make_repository_id,
)
from codegraph.retrieval.models import CodeChunk


class CodeChunker:
    """Extracts deterministic CodeChunks from a Phase 1 Repository model."""

    def chunk_repository(
        self,
        repository: Repository,
        source_code_map: dict[str, str | bytes],
    ) -> list[CodeChunk]:
        """Convert repository entities into searchable CodeChunk objects.

        Args:
            repository: Phase 1 Repository domain model.
            source_code_map: Dict mapping relative file path -> source code string or bytes.

        Returns:
            Deterministically sorted list of CodeChunk objects.
        """
        repo_id = make_repository_id(repository.root_path)
        chunks: list[CodeChunk] = []
        seen_chunk_ids: set[str] = set()

        for py_file in repository.files:
            source_raw = source_code_map.get(py_file.path)
            if not source_raw:
                continue

            source_text = (
                source_raw.decode("utf-8", errors="replace")
                if isinstance(source_raw, bytes)
                else source_raw
            )
            file_lines = source_text.splitlines()

            # 1. Class Chunks
            for cls in py_file.classes:
                c_id = make_class_id(py_file.module_name, cls.name)
                if c_id not in seen_chunk_ids:
                    seen_chunk_ids.add(c_id)
                    qname = self._make_qname(py_file.module_name, cls.name)
                    snippet = self._slice_source(file_lines, cls.location.start_line, cls.location.end_line)
                    chunks.append(
                        CodeChunk(
                            id=c_id,
                            entity_id=c_id,
                            repository_id=repo_id,
                            file_path=py_file.path,
                            module_name=py_file.module_name,
                            entity_type="class",
                            name=cls.name,
                            qualified_name=qname,
                            source_code=snippet,
                            start_line=cls.location.start_line,
                            start_column=cls.location.start_column,
                            end_line=cls.location.end_line,
                            end_column=cls.location.end_column,
                            metadata={"docstring": cls.docstring or ""},
                        )
                    )

                # Method Chunks
                for meth in cls.methods:
                    m_id = make_method_id(py_file.module_name, cls.name, meth.name)
                    if m_id not in seen_chunk_ids:
                        seen_chunk_ids.add(m_id)
                        m_qname = self._make_qname(py_file.module_name, f"{cls.name}.{meth.name}")
                        m_snippet = self._slice_source(file_lines, meth.location.start_line, meth.location.end_line)
                        chunks.append(
                            CodeChunk(
                                id=m_id,
                                entity_id=m_id,
                                repository_id=repo_id,
                                file_path=py_file.path,
                                module_name=py_file.module_name,
                                entity_type="method",
                                name=meth.name,
                                qualified_name=m_qname,
                                source_code=m_snippet,
                                start_line=meth.location.start_line,
                                start_column=meth.location.start_column,
                                end_line=meth.location.end_line,
                                end_column=meth.location.end_column,
                                metadata={
                                    "class_name": cls.name,
                                    "docstring": meth.docstring or "",
                                    "return_annotation": meth.return_annotation or "",
                                },
                            )
                        )

            # 2. Top-Level Function Chunks
            for fn in py_file.functions:
                fn_id = make_function_id(py_file.module_name, fn.name)
                if fn_id not in seen_chunk_ids:
                    seen_chunk_ids.add(fn_id)
                    fn_qname = self._make_qname(py_file.module_name, fn.name)
                    fn_snippet = self._slice_source(file_lines, fn.location.start_line, fn.location.end_line)
                    chunks.append(
                        CodeChunk(
                            id=fn_id,
                            entity_id=fn_id,
                            repository_id=repo_id,
                            file_path=py_file.path,
                            module_name=py_file.module_name,
                            entity_type="function",
                            name=fn.name,
                            qualified_name=fn_qname,
                            source_code=fn_snippet,
                            start_line=fn.location.start_line,
                            start_column=fn.location.start_column,
                            end_line=fn.location.end_line,
                            end_column=fn.location.end_column,
                            metadata={
                                "docstring": fn.docstring or "",
                                "return_annotation": fn.return_annotation or "",
                            },
                        )
                    )

        # Sort chunks deterministically by ID
        chunks.sort(key=lambda c: c.id)
        return chunks

    def _slice_source(self, lines: list[str], start_line: int, end_line: int) -> str:
        """Slice source code lines from start_line to end_line (inclusive, 0-based)."""
        if 0 <= start_line < len(lines):
            end_idx = min(end_line + 1, len(lines))
            return "\n".join(lines[start_line:end_idx])
        return ""

    def _make_qname(self, module_name: str, symbol_name: str) -> str:
        if not module_name or module_name in ("__init__", "__root__"):
            return symbol_name
        return f"{module_name}.{symbol_name}"
