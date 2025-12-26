"""
Document index builder.

The UI expects a document catalog shaped like:
  { category: { year: [ {id, label, year, pdf_rel_path, vs_rel_path}, ... ] } }

In production, we derive this from Azure Blob Storage by listing vectorstore
artifacts under a prefix like:
  vectorstores_RecursiveSplitting/<folder_path>/<pdf_name>/index.faiss

We infer:
  - doc_id        = <folder_path>/<pdf_name>
  - category      = first path segment of doc_id
  - year          = second path segment of doc_id (or 'root' if missing)
  - label         = remaining segments joined by '/' (or doc_id leaf if shallow)
  - pdf_rel_path  = doc_id + '.pdf'  (served from the separate `pdfs/` prefix)

This preserves your folder structure while keeping the existing dropdown UI.
"""

from __future__ import annotations

from typing import Any

from storage.blob import BlobStorageClient


def build_doc_index_from_blob(blob: BlobStorageClient, vectorstore_prefix: str) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """
    Build a browsable index by scanning for `index.faiss` blobs.

    Parameters
    ----------
    blob:
        Initialized BlobStorageClient for the container holding vectorstores.
    vectorstore_prefix:
        Prefix where vectorstores live (e.g. 'vectorstores_RecursiveSplitting').
    """

    index: dict[str, dict[str, list[dict[str, Any]]]] = {}
    prefix = vectorstore_prefix.strip("/").rstrip("/") + "/"

    for blob_name in blob.list_blobs(prefix):
        if not blob_name.endswith("/index.faiss"):
            continue

        # blob_name: <prefix><doc_id>/index.faiss
        doc_id = blob_name[len(prefix) : -len("/index.faiss")]
        if not doc_id:
            continue

        parts = [p for p in doc_id.split("/") if p]
        category = parts[0] if len(parts) >= 1 else "root"
        year = parts[1] if len(parts) >= 2 else "root"
        label = "/".join(parts[2:]) if len(parts) > 2 else (parts[-1] if parts else doc_id)

        doc = {
            "id": doc_id,
            "label": label,
            "year": year,
            "pdf_rel_path": f"{doc_id}.pdf",
            "vs_rel_path": doc_id,
        }

        index.setdefault(category, {}).setdefault(year, []).append(doc)

    # Sort for stable dropdown ordering
    for cat in index:
        for year in index[cat]:
            index[cat][year] = sorted(index[cat][year], key=lambda x: x["label"])

    return index


