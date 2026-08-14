"""Unit tests for InvestigationManager and FileInvestigationStore."""

from pathlib import Path
from codegraph.platform.investigations.manager import InvestigationManager
from codegraph.platform.investigations.store import FileInvestigationStore


def test_investigation_creation_and_persistence(tmp_path: Path) -> None:
    store = FileInvestigationStore(storage_dir=tmp_path)
    manager = InvestigationManager(store=store)

    rec = manager.create_investigation(
        question="Why did authentication fail?",
        repository_id="repository:sample_project",
        hypotheses=["Password hash mismatch"],
        evidence=["[E1] File services.py L20"],
        citations=["services.py:L20"],
        final_answer="Authentication failed due to password hash mismatch.",
    )

    assert rec.investigation_id.startswith("inv_")
    assert rec.question == "Why did authentication fail?"

    fetched = manager.get_investigation(rec.investigation_id)
    assert fetched is not None
    assert fetched.final_answer == rec.final_answer

    trace_id = manager.get_investigation_trace(rec.investigation_id)
    assert trace_id == rec.trace_id
