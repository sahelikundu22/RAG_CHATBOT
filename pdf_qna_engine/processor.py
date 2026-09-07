import io
from pathlib import Path
from typing import List, Tuple, Union
import numpy as np
from pypdf import PdfReader
from pdf_qna_engine.model import load_embedding_model


def extract_pages(pdf_file) -> List[dict]:
    """Extract text page-by-page using pypdf as in internship_test1.py."""
    if isinstance(pdf_file, (bytes, bytearray)):
        pdf_file = io.BytesIO(pdf_file)
    elif hasattr(pdf_file, "getvalue"):  # Streamlit UploadedFile
        pdf_file = io.BytesIO(pdf_file.getvalue())
    elif isinstance(pdf_file, (str, Path)):
        p = Path(pdf_file)
        if p.is_file():
            with open(p, "rb") as f:
                pdf_file = io.BytesIO(f.read())

    reader = PdfReader(pdf_file)
    documents = []
    for page_number, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            documents.append({
                "text": text,
                "page": page_number + 1,
            })
    return documents


def extract_text(pdf_file) -> str:
    """Extract full raw text using pypdf."""
    if isinstance(pdf_file, str):
        p = Path(pdf_file)
        if not p.is_file():
            # Raw text was passed
            return pdf_file

    docs = extract_pages(pdf_file)
    return "\n\n".join(doc["text"].strip() for doc in docs if doc["text"].strip())


def split_text(text_or_docs: Union[str, List[dict]], chunk_size: int = 5000, overlap: int = 200) -> List[str]:
    """
    Character-based chunking with chunk_size=5000 and overlap=200
    matching internship_test1.py.
    """
    if isinstance(text_or_docs, str):
        text = text_or_docs.strip()
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start += chunk_size - overlap
        return chunks

    chunks = []
    for doc in text_or_docs:
        text = doc.get("text", "")
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start += chunk_size - overlap
    return chunks


def create_embeddings(chunks: List[str]) -> np.ndarray:
    """Generate embeddings using BAAI/bge-small-en-v1.5."""
    if not chunks:
        return np.empty((0, 384), dtype=np.float32)
    model = load_embedding_model()
    embeddings = model.embed_documents(chunks)
    return np.array(embeddings, dtype=np.float32)


def process_text(text: str) -> Tuple[List[str], np.ndarray]:
    chunks = split_text(text)
    embeddings = create_embeddings(chunks)
    return chunks, embeddings