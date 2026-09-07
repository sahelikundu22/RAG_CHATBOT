import pdfplumber
from pdf_qna_engine.model import load_embedding_model
from typing import List, Tuple
import numpy as np
import io

def extract_text(pdf_file) -> str:
    if isinstance(pdf_file, bytes):
        pdf_file = io.BytesIO(pdf_file)
    text_parts = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
    return "\n\n".join(text_parts)

def split_text(text: str, chunk_size: int = 150, overlap: int = 30) -> List[str]:
    if not text.strip():
        return []
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks

def create_embeddings(chunks: List[str]) -> np.ndarray:
    model = load_embedding_model()
    return model.encode(chunks, show_progress_bar=False, convert_to_numpy=True)

def process_text(text: str) -> Tuple[List[str], np.ndarray]:
    chunks = split_text(text)
    embeddings = create_embeddings(chunks)
    return chunks, embeddings