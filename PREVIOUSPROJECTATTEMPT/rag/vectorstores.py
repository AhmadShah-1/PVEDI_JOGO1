"""
Vectorstore loading and caching.

Vectorstores are stored in Azure Blob Storage as directories (prefixes) created
by FAISS' `save_local()`:
  <vectorstore_prefix>/<doc_id>/index.faiss
  <vectorstore_prefix>/<doc_id>/index.pkl

Because FAISS expects local filesystem files, the web app downloads those
artifacts into a local cache directory and loads them via `FAISS.load_local(...)`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from langchain_community.vectorstores import FAISS

from storage.blob import BlobSettings, BlobStorageClient


def default_cache_dir() -> Path:
    # App Service (Linux) supports /tmp; on Windows use a local folder.
    if os.name == "nt":
        return Path(os.getcwd()) / "rag_cache"
    return Path(os.environ.get("RAG_CACHE_DIR", "/tmp/rag_cache"))


@dataclass
class VectorstoreManager:
    """
    Loads FAISS vectorstores from Blob into a local cache.

    Parameters
    ----------
    blob:
        Blob storage client.
    settings:
        Blob settings (contains vectorstore prefix).
    embeddings:
        The embedding function used for retrieval (must match the one used to build the FAISS index).
    cache_root:
        Local directory where vectorstores will be downloaded and cached.
    """

    blob: BlobStorageClient
    settings: BlobSettings
    embeddings: object
    cache_root: Path

    def __post_init__(self) -> None:
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self._mem_cache: dict[str, FAISS] = {}

    def _local_dir_for_doc(self, doc_id: str) -> Path:
        # Keep paths safe for filesystem usage.
        safe = doc_id.replace("\\", "/").replace("/", "__")
        return self.cache_root / safe

    def _is_cached_on_disk(self, local_dir: Path) -> bool:
        return (local_dir / "index.faiss").exists() and (local_dir / "index.pkl").exists()

    def get_vectorstore(self, doc_id: str) -> FAISS:
        """
        Get (and cache) a FAISS vectorstore for the given doc_id.

        Downloads artifacts from Blob on first use.
        """
        if doc_id in self._mem_cache:
            return self._mem_cache[doc_id]

        local_dir = self._local_dir_for_doc(doc_id)
        if not self._is_cached_on_disk(local_dir):
            prefix = f"{self.settings.vectorstore_prefix.strip('/')}/{doc_id.strip('/')}/"
            self.blob.download_prefix(prefix, local_dir)

        # NOTE: FAISS.load_local() uses pickle for docstore metadata (`index.pkl`).
        # We set allow_dangerous_deserialization=True because we control the blob content.
        vs = FAISS.load_local(
            str(local_dir),
            self.embeddings,
            allow_dangerous_deserialization=True,
        )
        self._mem_cache[doc_id] = vs
        return vs


