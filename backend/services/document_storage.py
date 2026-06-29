"""Document storage boundary used by uploads and document readers."""
import os
import mimetypes
import threading
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Protocol


PATH_ESCAPE_ERROR = "document path escapes storage root"


@dataclass(frozen=True)
class StoredDocument:
    relative_path: str
    local_path: Path
    storage_uri: str


class DocumentStorage(Protocol):
    def save_upload(self, department: str, filename: str, data: bytes) -> StoredDocument:
        """Persist upload bytes and return their stable storage location."""

    def resolve_local_path(self, relative_path: str) -> Path:
        """Resolve a stored document to a local path for parsing or serving."""

    def delete(self, relative_path: str) -> None:
        """Delete a stored object if it exists."""


class LocalDocumentStorage:
    """Filesystem-backed storage for local development and tests."""

    _write_lock = threading.Lock()

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save_upload(self, department: str, filename: str, data: bytes) -> StoredDocument:
        safe_name = _safe_filename(filename)
        department_dir = self.root / department.lower()
        department_dir.mkdir(parents=True, exist_ok=True)

        with self._write_lock:
            destination = _available_destination(department_dir, safe_name)
            temp_path = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
            try:
                with temp_path.open("wb") as output:
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
                temp_path.replace(destination)
            finally:
                temp_path.unlink(missing_ok=True)

        relative_path = destination.relative_to(self.root).as_posix()
        return StoredDocument(
            relative_path=relative_path,
            local_path=destination,
            storage_uri=destination.as_uri(),
        )

    def resolve_local_path(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(PATH_ESCAPE_ERROR) from exc
        return candidate

    def delete(self, relative_path: str) -> None:
        self.resolve_local_path(relative_path).unlink(missing_ok=True)


class GcsDocumentStorage:
    """GCS-backed immutable upload objects with an atomic local read cache."""

    _cache_lock = threading.Lock()

    def __init__(
        self,
        bucket_name: str,
        cache_root: Path,
        *,
        prefix: str = "uploads",
        client=None,
    ):
        if not bucket_name.strip():
            raise ValueError("bucket_name is required")
        if client is None:
            from google.cloud import storage

            client = storage.Client()
        self.bucket_name = bucket_name
        self.bucket = client.bucket(bucket_name)
        self.cache_root = cache_root.resolve()
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self.prefix = _normalize_relative_path(prefix)

    def save_upload(self, department: str, filename: str, data: bytes) -> StoredDocument:
        safe_name = _safe_filename(filename)
        base_key = f"{self.prefix}/{department.lower()}/{safe_name}"
        object_key = base_key
        blob = self.bucket.blob(object_key)
        if blob.exists():
            suffix = Path(safe_name).suffix
            stem = Path(safe_name).stem
            object_key = (
                f"{self.prefix}/{department.lower()}/"
                f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
            )
            blob = self.bucket.blob(object_key)
        content_type = mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
        blob.upload_from_string(data, content_type=content_type)
        local_path = self._cache_path(object_key)
        _atomic_write(local_path, data)
        return StoredDocument(
            relative_path=object_key,
            local_path=local_path,
            storage_uri=f"gs://{self.bucket_name}/{object_key}",
        )

    def resolve_local_path(self, relative_path: str) -> Path:
        object_key = _normalize_relative_path(relative_path)
        local_path = self._cache_path(object_key)
        if local_path.exists():
            return local_path
        with self._cache_lock:
            if local_path.exists():
                return local_path
            local_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = local_path.with_name(
                f".{local_path.name}.{uuid.uuid4().hex}.tmp"
            )
            try:
                self.bucket.blob(object_key).download_to_filename(str(temp_path))
                temp_path.replace(local_path)
            finally:
                temp_path.unlink(missing_ok=True)
        return local_path

    def delete(self, relative_path: str) -> None:
        object_key = _normalize_relative_path(relative_path)
        blob = self.bucket.blob(object_key)
        if blob.exists():
            blob.delete()
        self._cache_path(object_key).unlink(missing_ok=True)

    def _cache_path(self, object_key: str) -> Path:
        candidate = (self.cache_root / object_key).resolve()
        try:
            candidate.relative_to(self.cache_root)
        except ValueError as exc:
            raise ValueError(PATH_ESCAPE_ERROR) from exc
        return candidate


class RoutedDocumentStorage:
    """Keep bundled manifest files local while routing upload keys remotely."""

    def __init__(self, local, uploads, upload_prefix: str):
        self.local = local
        self.uploads = uploads
        self.upload_prefix = _normalize_relative_path(upload_prefix).rstrip("/") + "/"

    def save_upload(self, department: str, filename: str, data: bytes) -> StoredDocument:
        return self.uploads.save_upload(department, filename, data)

    def resolve_local_path(self, relative_path: str) -> Path:
        if relative_path.startswith(self.upload_prefix):
            return self.uploads.resolve_local_path(relative_path)
        return self.local.resolve_local_path(relative_path)

    def delete(self, relative_path: str) -> None:
        if relative_path.startswith(self.upload_prefix):
            self.uploads.delete(relative_path)
        else:
            self.local.delete(relative_path)


@lru_cache(maxsize=1)
def get_document_storage() -> DocumentStorage:
    from backend.config import (
        DOCUMENT_CACHE_DIR,
        DOCUMENT_STORAGE_BACKEND,
        DOCUMENTS_DIR,
        GCS_DOCUMENT_BUCKET,
        GCS_DOCUMENT_PREFIX,
    )

    local = LocalDocumentStorage(DOCUMENTS_DIR)
    if DOCUMENT_STORAGE_BACKEND == "local":
        return local
    uploads = GcsDocumentStorage(
        GCS_DOCUMENT_BUCKET,
        DOCUMENT_CACHE_DIR,
        prefix=GCS_DOCUMENT_PREFIX,
    )
    return RoutedDocumentStorage(local, uploads, GCS_DOCUMENT_PREFIX)


def _safe_filename(filename: str) -> str:
    basename = Path(filename or "upload").name
    safe_name = "".join(
        character if character.isalnum() or character in "._-" else "_"
        for character in basename
    )
    if safe_name in {"", ".", ".."}:
        return "upload"
    return safe_name


def _available_destination(directory: Path, filename: str) -> Path:
    destination = directory / filename
    if not destination.exists():
        return destination
    suffix = destination.suffix
    return directory / f"{destination.stem}_{uuid.uuid4().hex[:8]}{suffix}"


def _normalize_relative_path(value: str) -> str:
    path = PurePosixPath(str(value).replace("\\", "/"))
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(PATH_ESCAPE_ERROR)
    return path.as_posix()


def _atomic_write(destination: Path, data: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temp_path.open("wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        temp_path.replace(destination)
    finally:
        temp_path.unlink(missing_ok=True)