"""Ingestion package for scanning, parsing, extracting, and orchestrating repository ingestion."""

from .extractor import PythonExtractor
from .ingestor import RepositoryIngestor
from .parser import ParseResult, PythonParser
from .scanner import DEFAULT_IGNORE_DIRS, scan_repository

__all__ = [
    "scan_repository",
    "DEFAULT_IGNORE_DIRS",
    "PythonParser",
    "ParseResult",
    "PythonExtractor",
    "RepositoryIngestor",
]
