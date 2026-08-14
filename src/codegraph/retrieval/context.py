"""Context Builder for formatting fused retrieval results into structured context objects."""

from typing import Mapping, Sequence
from codegraph.retrieval.models import CodeChunk, ContextItem, FusedResult


class ContextBuilder:
    """Converts ranked FusedResults into structured ContextItem objects for downstream LLM usage."""

    def build(
        self,
        results: Sequence[FusedResult],
        max_items: int = 10,
        chunk_map: Mapping[str, CodeChunk] | None = None,
    ) -> list[ContextItem]:
        """Build structured context list from fused retrieval results.

        Args:
            results: Sequence of FusedResult items sorted by rank.
            max_items: Maximum number of context items to generate.
            chunk_map: Optional mapping of entity_id/chunk_id -> CodeChunk for source code payload.

        Returns:
            List of ContextItem objects preserving source grounding metadata.
        """
        chunk_lookup = chunk_map or {}
        context_items: list[ContextItem] = []

        for item in results[:max_items]:
            chunk = chunk_lookup.get(item.entity_id) or chunk_lookup.get(item.chunk_id)

            file_path = item.metadata.get("file_path") or (chunk.file_path if chunk else "")
            qname = item.metadata.get("qualified_name") or (chunk.qualified_name if chunk else item.entity_id)
            start_line = item.metadata.get("start_line", chunk.start_line if chunk else 0)
            end_line = item.metadata.get("end_line", chunk.end_line if chunk else 0)
            source_code = chunk.source_code if chunk else ""

            context_items.append(
                ContextItem(
                    entity_id=item.entity_id,
                    file_path=file_path,
                    qualified_name=qname,
                    start_line=start_line,
                    end_line=end_line,
                    retrieved_by=item.sources,
                    score=item.score,
                    source_code=source_code,
                )
            )

        return context_items
