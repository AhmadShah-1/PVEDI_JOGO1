"""
Azure Blob Storage utilities.

This module provides a small wrapper around `azure-storage-blob` for:
  - checking existence of blobs
  - downloading all blobs under a prefix into a local directory
  - streaming a blob (used for serving PDFs)

Environment variables:
  - AZURE_STORAGE_CONNECTION_STRING (required in production)
  - AZURE_BLOB_CONTAINER (default: nyccodesvectorstore)
  - AZURE_BLOB_PDF_PREFIX (default: pdfs)
  - AZURE_BLOB_VECTORSTORE_PREFIX (default: vectorstores_RecursiveSplitting)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from azure.storage.blob import BlobServiceClient, ContainerClient


def _env(name: str, default: str | None = None) -> str | None:
    val = os.environ.get(name)
    if val is None:
        return default
    val = val.strip()
    return val or default


@dataclass(frozen=True)
class BlobSettings:
    """Configuration for Azure Blob Storage access."""

    connection_string: str
    container: str
    pdf_prefix: str
    vectorstore_prefix: str

    @staticmethod
    def from_env() -> "BlobSettings":
        conn = _env("AZURE_STORAGE_CONNECTION_STRING")
        if not conn:
            raise RuntimeError(
                "Missing AZURE_STORAGE_CONNECTION_STRING. Set it in Azure App Service Configuration "
                "or your local environment before starting."
            )

        container = _env("AZURE_BLOB_CONTAINER", "nyccodesvectorstore") or "nyccodesvectorstore"
        pdf_prefix = (_env("AZURE_BLOB_PDF_PREFIX", "pdfs") or "pdfs").strip("/")
        vs_prefix = (_env("AZURE_BLOB_VECTORSTORE_PREFIX", "vectorstores_RecursiveSplitting") or "vectorstores_RecursiveSplitting").strip("/")

        return BlobSettings(
            connection_string=conn,
            container=container,
            pdf_prefix=pdf_prefix,
            vectorstore_prefix=vs_prefix,
        )


class BlobStorageClient:
    """Thin wrapper around Azure Blob container operations."""

    def __init__(self, container: ContainerClient):
        self._container = container

    @staticmethod
    def from_env() -> "BlobStorageClient":
        settings = BlobSettings.from_env()
        svc = BlobServiceClient.from_connection_string(settings.connection_string)
        container = svc.get_container_client(settings.container)
        return BlobStorageClient(container)

    @property
    def container(self) -> ContainerClient:
        return self._container

    def blob_exists(self, name: str) -> bool:
        """Return True if a blob exists."""
        return self._container.get_blob_client(name).exists()

    def list_blobs(self, prefix: str) -> Iterable[str]:
        """List blob names under a prefix."""
        for b in self._container.list_blobs(name_starts_with=prefix):
            yield b.name

    def download_blob_to_file(self, blob_name: str, local_path: Path) -> None:
        """Download a single blob to a local file path."""
        local_path.parent.mkdir(parents=True, exist_ok=True)
        blob = self._container.get_blob_client(blob_name)
        stream = blob.download_blob()
        with local_path.open("wb") as f:
            stream.readinto(f)

    def download_prefix(self, prefix: str, local_dir: Path) -> list[Path]:
        """
        Download all blobs under `prefix` into `local_dir`.

        Returns a list of downloaded local file paths.
        """
        downloaded: list[Path] = []
        prefix = prefix.rstrip("/") + "/"
        local_dir.mkdir(parents=True, exist_ok=True)

        for blob_name in self.list_blobs(prefix):
            rel = blob_name[len(prefix) :]
            if not rel or rel.endswith("/"):
                continue
            local_path = local_dir / rel
            self.download_blob_to_file(blob_name, local_path)
            downloaded.append(local_path)

        return downloaded

    def stream_blob(self, blob_name: str, chunk_size: int = 4 * 1024 * 1024) -> Iterator[bytes]:
        """
        Stream a blob as an iterator of bytes.

        Note: pdf.js often requests ranges; for simplicity we stream the full file.
        """
        blob = self._container.get_blob_client(blob_name)
        downloader = blob.download_blob()
        for chunk in downloader.chunks(chunk_size=chunk_size):
            yield chunk


