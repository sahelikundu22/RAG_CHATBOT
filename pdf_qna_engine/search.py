import chromadb
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple
from pdf_qna_engine.model import load_embedding_model

_chroma_client = None
_chroma_collection = None
_active_collection_key: Optional[str] = None
stored_chunks: List[str] = []


def build_chroma_vectorstore(
    chunks: List[str],
    embeddings: Optional[np.ndarray] = None,
    collection_name: str = "pdf_docs",
    persist_dir: Optional[Path | str] = None,
    collection_key: Optional[str] = None,
) -> None:
    """
    Build or load a Chroma collection from pre-computed embeddings.
    The embedding model is NOT loaded here; it is only needed at query time.
    This avoids re-embedding chunks that were already embedded and saved to disk.
    """
    global _chroma_client, _chroma_collection, _active_collection_key, stored_chunks
    stored_chunks = list(chunks)
    key = collection_key or (str(persist_dir) if persist_dir else collection_name)

    if _chroma_collection is not None and _active_collection_key == key:
        return

    if persist_dir:
        chroma_dir = Path(persist_dir) / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(chroma_dir))
    else:
        _chroma_client = chromadb.EphemeralClient()

    _chroma_collection = _chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    existing_count = _chroma_collection.count()
    if existing_count == len(stored_chunks) and existing_count > 0:
        _active_collection_key = key
        return
    if existing_count and existing_count != len(stored_chunks):
        _chroma_client.delete_collection(collection_name)
        _chroma_collection = _chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    if not stored_chunks:
        _active_collection_key = key
        return

    if embeddings is not None and len(embeddings) > 0:
        emb_list = embeddings.astype(np.float32).tolist()
    else:
        model = load_embedding_model()
        emb_list = model.embed_documents(stored_chunks)

    _chroma_collection.upsert(
        embeddings=emb_list,
        documents=stored_chunks,
        ids=[str(i) for i in range(len(stored_chunks))],
    )
    _active_collection_key = key


def build_faiss_index(
    chunks: List[str],
    embeddings: Optional[np.ndarray] = None,
    persist_dir: Optional[Path | str] = None,
    collection_key: Optional[str] = None,
):
    """Backward-compatible alias; the app now uses Chroma under the hood."""
    return build_chroma_vectorstore(
        chunks,
        embeddings,
        persist_dir=persist_dir,
        collection_key=collection_key,
    )


def search_chunks(question: str, top_k: int = 3) -> Tuple[List[str], List[float]]:
    """
    Embed the query using the model (loaded/cached once per session),
    then search the Chroma collection.
    """
    global _chroma_collection, stored_chunks
    if _chroma_collection is None:
        raise ValueError("Chroma collection not built. Call build_faiss_index() first.")
    result_count = _chroma_collection.count()
    if result_count == 0:
        return [], []

    # Model is loaded here (only when user asks a question), cached by @st.cache_resource
    model = load_embedding_model()
    query_embedding = model.embed_query(question)

    results = _chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, result_count),
        include=["documents", "distances"],
    )

    top_chunks = results["documents"][0]
    # Chroma cosine distances are in [0, 2]; convert to similarity in [0, 1]
    top_scores = [1.0 - (d / 2.0) for d in results["distances"][0]]
    return top_chunks, top_scores
