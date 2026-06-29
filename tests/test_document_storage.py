import pytest

from backend.services.document_storage import (
    GcsDocumentStorage,
    LocalDocumentStorage,
    RoutedDocumentStorage,
)


def test_local_storage_sanitizes_paths_and_round_trips_bytes(tmp_path):
    storage = LocalDocumentStorage(tmp_path / "documents")

    stored = storage.save_upload(
        "Engineering",
        "../unsafe report.md",
        b"# trusted bytes",
    )

    assert stored.relative_path == "engineering/unsafe_report.md"
    assert stored.local_path.read_bytes() == b"# trusted bytes"
    assert storage.resolve_local_path(stored.relative_path) == stored.local_path


def test_local_storage_avoids_overwrite_and_deletes_exact_object(tmp_path):
    storage = LocalDocumentStorage(tmp_path / "documents")
    first = storage.save_upload("HR", "policy.md", b"v1")
    second = storage.save_upload("HR", "policy.md", b"v2")

    assert first.relative_path != second.relative_path
    assert first.local_path.read_bytes() == b"v1"
    assert second.local_path.read_bytes() == b"v2"

    storage.delete(second.relative_path)
    assert first.local_path.exists()
    assert not second.local_path.exists()


def test_local_storage_rejects_escape_during_resolution(tmp_path):
    storage = LocalDocumentStorage(tmp_path / "documents")

    with pytest.raises(ValueError, match="escapes storage root"):
        storage.resolve_local_path("../secret.txt")


def test_gcs_storage_round_trips_cache_and_stable_uri(tmp_path):
    client = FakeClient()
    storage = GcsDocumentStorage(
        "documents-bucket",
        tmp_path / "cache",
        client=client,
    )

    stored = storage.save_upload("Engineering", "../runbook.md", b"# runbook")

    assert stored.relative_path == "uploads/engineering/runbook.md"
    assert stored.storage_uri == "gs://documents-bucket/uploads/engineering/runbook.md"
    assert stored.local_path.read_bytes() == b"# runbook"
    stored.local_path.unlink()
    assert storage.resolve_local_path(stored.relative_path).read_bytes() == b"# runbook"
    storage.delete(stored.relative_path)
    assert stored.relative_path not in client.objects


def test_routed_storage_keeps_manifest_local_and_uploads_remote(tmp_path):
    local = LocalDocumentStorage(tmp_path / "documents")
    manifest = local.save_upload("Engineering", "architecture.md", b"local")
    client = FakeClient()
    remote = GcsDocumentStorage("bucket", tmp_path / "cache", client=client)
    routed = RoutedDocumentStorage(local, remote, "uploads")
    uploaded = routed.save_upload("HR", "policy.md", b"remote")

    assert routed.resolve_local_path(manifest.relative_path).read_bytes() == b"local"
    assert routed.resolve_local_path(uploaded.relative_path).read_bytes() == b"remote"


class FakeBlob:
    def __init__(self, objects, key):
        self.objects = objects
        self.key = key

    def exists(self):
        return self.key in self.objects

    def upload_from_string(self, data, content_type=None):
        self.objects[self.key] = bytes(data)

    def download_to_filename(self, filename):
        with open(filename, "wb") as destination:
            destination.write(self.objects[self.key])

    def delete(self):
        self.objects.pop(self.key, None)


class FakeBucket:
    def __init__(self, objects):
        self.objects = objects

    def blob(self, key):
        return FakeBlob(self.objects, key)


class FakeClient:
    def __init__(self):
        self.objects = {}

    def bucket(self, bucket_name):
        return FakeBucket(self.objects)