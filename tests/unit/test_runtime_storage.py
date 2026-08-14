"""Unit tests for PlatformStore and Metadata Records."""

from codegraph.runtime.storage.models import OrganizationRecord, RepositoryVersionRecord, UserRecord
from codegraph.runtime.storage.store import MemoryPlatformStore


def test_platform_store_crud() -> None:
    store = MemoryPlatformStore()

    user = UserRecord(user_id="usr_001", username="dev_user", email="dev@codegraph.io", organization_id="org_001")
    store.save_user(user)
    assert store.get_user("usr_001") == user

    org = OrganizationRecord(organization_id="org_001", name="Acme Engineering")
    store.save_organization(org)
    assert store.get_organization("org_001") == org

    ver = RepositoryVersionRecord(version_id="ver_001", repository_id="repo:sample", commit_sha="abc1234")
    store.save_repository_version(ver)
    assert store.get_repository_version("repo:sample", "abc1234") == ver
