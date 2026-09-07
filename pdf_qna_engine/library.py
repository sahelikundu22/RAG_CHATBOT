from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Dict, List

import numpy as np
try:
    import streamlit as st
except ModuleNotFoundError:
    st = None

from pdf_qna_engine.processor import extract_text, process_text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_ROOT = PROJECT_ROOT / "documents"
INDEX_ROOT = PROJECT_ROOT / "storage" / "pdf_indexes"


@dataclass(frozen=True)
class IndexedPdf:
    name: str
    path: Path
    cache_dir: Path
    pdf_bytes: bytes
    raw_text: str
    chunks: List[str]
    embeddings: np.ndarray


def available_pdfs() -> Dict[str, Path]:
    if not DOCUMENTS_ROOT.exists():
        return {}

    return {
        path.stem.replace("_", " ").title(): path
        for path in sorted(DOCUMENTS_ROOT.glob("*.pdf"))
    }


def cache_dir_for(name: str) -> Path:
    safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return INDEX_ROOT / safe_name


PIPELINE_VERSION = "bge-small-en-v1.5-char5000"


def is_index_cached(name: str) -> bool:
    pdfs = available_pdfs()
    if name not in pdfs:
        return False

    path = pdfs[name]
    cache_dir = cache_dir_for(name)
    metadata_path = cache_dir / "metadata.json"
    embeddings_path = cache_dir / "embeddings.npy"

    if not metadata_path.exists() or not embeddings_path.exists():
        return False

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False

    return (
        metadata.get("source_path") == str(path)
        and metadata.get("source_size") == path.stat().st_size
        and metadata.get("source_modified_time") == path.stat().st_mtime
        and metadata.get("pipeline_version") == PIPELINE_VERSION
    )


def _load_from_disk(name: str, path: Path, pdf_bytes: bytes) -> IndexedPdf:
    cache_dir = cache_dir_for(name)
    metadata = json.loads((cache_dir / "metadata.json").read_text(encoding="utf-8"))
    embeddings = np.load(cache_dir / "embeddings.npy")

    return IndexedPdf(
        name=name,
        path=path,
        cache_dir=cache_dir,
        pdf_bytes=pdf_bytes,
        raw_text=metadata["raw_text"],
        chunks=metadata["chunks"],
        embeddings=embeddings,
    )


def _save_to_disk(indexed_pdf: IndexedPdf) -> None:
    cache_dir = cache_dir_for(indexed_pdf.name)
    cache_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "name": indexed_pdf.name,
        "pipeline_version": PIPELINE_VERSION,
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "source_path": str(indexed_pdf.path),
        "source_size": indexed_pdf.path.stat().st_size,
        "source_modified_time": indexed_pdf.path.stat().st_mtime,
        "raw_text": indexed_pdf.raw_text,
        "chunks": indexed_pdf.chunks,
    }

    (cache_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    np.save(cache_dir / "embeddings.npy", indexed_pdf.embeddings)



def _cache_resource(**kwargs):
    if st is None:
        return lambda function: function
    return st.cache_resource(**kwargs)


@_cache_resource(show_spinner="Indexing PDF...")
def load_indexed_pdf(
    name: str,
    path_text: str,
    modified_time: float,
    source_size: int,
) -> IndexedPdf:
    path = Path(path_text)
    pdf_bytes = path.read_bytes()

    if is_index_cached(name):
        return _load_from_disk(name, path, pdf_bytes)

    raw_text = extract_text(pdf_bytes)
    chunks, embeddings = process_text(raw_text)

    indexed_pdf = IndexedPdf(
        name=name,
        path=path,
        cache_dir=cache_dir_for(name),
        pdf_bytes=pdf_bytes,
        raw_text=raw_text,
        chunks=chunks,
        embeddings=embeddings,
    )
    _save_to_disk(indexed_pdf)

    return indexed_pdf


def get_indexed_pdf(name: str) -> IndexedPdf:
    pdfs = available_pdfs()
    if name not in pdfs:
        raise FileNotFoundError(f"PDF not found in documents folder: {name}")

    path = pdfs[name]
    stat = path.stat()
    return load_indexed_pdf(name, str(path), stat.st_mtime, stat.st_size)
