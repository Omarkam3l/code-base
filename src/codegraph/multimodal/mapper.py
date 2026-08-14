"""Code mapping engine connecting visual/document entities to CodeGraph code entities."""

from codegraph.domain.entities import Repository
from codegraph.multimodal.models import ConfidenceLevel, VisualEntity


class MultimodalCodeMapper:
    """Maps extracted visual and document entities to concrete CodeGraph AST/graph nodes."""

    def __init__(self, code_symbols: set[str] | None = None) -> None:
        self.code_symbols = code_symbols or {"UserService", "User", "AuthenticationMiddleware", "BaseService", "AuthService", "Order"}

    def map_entity(self, entity: VisualEntity) -> tuple[str | None, ConfidenceLevel]:
        """Attempt to map visual entity to real code symbol."""
        # 1. Exact qualified or symbol match
        if entity.name in self.code_symbols:
            return entity.name, ConfidenceLevel.HIGH

        # 2. Normalized name match (e.g. AuthService -> AuthService)
        clean_name = entity.name.replace(" ", "").replace("_", "")
        for sym in self.code_symbols:
            if clean_name.lower() == sym.lower():
                return sym, ConfidenceLevel.HIGH

        # 3. Substring matching
        for sym in self.code_symbols:
            if sym.lower() in clean_name.lower() or clean_name.lower() in sym.lower():
                return sym, ConfidenceLevel.MEDIUM

        return None, ConfidenceLevel.LOW
