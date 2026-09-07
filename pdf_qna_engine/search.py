from typing import List, Tuple
import numpy as np
import faiss
from pdf_qna_engine.model import load_embedding_model

faiss_index = None
faiss_chunks = None

def build_faiss_index(chunks: List[str], embeddings: np.ndarray):
    global faiss_index, faiss_chunks
    faiss_chunks = chunks
    normalized_embeddings = embeddings.astype(np.float32).copy()
    faiss_index = faiss.IndexFlatIP(embeddings.shape[1])
    faiss.normalize_L2(normalized_embeddings)
    faiss_index.add(normalized_embeddings)

def search_chunks(question: str, top_k: int = 2) -> Tuple[List[str], List[float]]:
    global faiss_index, faiss_chunks
    if faiss_index is None or faiss_chunks is None:
        raise ValueError("FAISS index not built. Call build_faiss_index() first.")

    model = load_embedding_model()
    query_embedding = model.encode([question], convert_to_numpy=True)
    faiss.normalize_L2(query_embedding)

    distances, indices = faiss_index.search(query_embedding.astype(np.float32), top_k)
    top_chunks = [faiss_chunks[i] for i in indices[0]]
    top_scores = [float(d) for d in distances[0]]
    return top_chunks, top_scores
