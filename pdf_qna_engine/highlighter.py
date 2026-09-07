import io
import re
import pdfplumber
from typing import List, Optional


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_highlight_coords(pdf_bytes: bytes, answer: str, contexts: List[str] = None) -> Optional[List[dict]]:
    if not answer or len(answer.strip()) < 3:
        return None

    # Prefer searching using the retrieved source chunks (verbatim from the PDF)
    # over the LLM's paraphrased answer, since the answer often won't match exactly.
    search_source = " ".join(contexts) if contexts else answer

    answer_words = set(normalize(answer).split())

    # From the source chunk(s), find the sentence(s) with the most word-overlap
    # with the answer — this approximates "what part of the source was actually used".
    source_sentences = [s.strip() for s in re.split(r"[.\n]", search_source) if s.strip()]

    scored = []
    for sent in source_sentences:
        sent_words = set(normalize(sent).split())
        if not sent_words:
            continue
        overlap = len(sent_words & answer_words) / len(sent_words)
        scored.append((overlap, sent))

    scored.sort(key=lambda x: x[0], reverse=True)

    candidates = [s for _, s in scored[:3] if s]

    # Fallback to old behavior if no context provided or no good overlap found
    if not candidates:
        sentences = [s.strip() for s in answer.split(".") if s.strip()]
        if len(sentences) >= 2:
            candidates.append(" ".join(sentences[:2]))
        if sentences:
            candidates.append(sentences[0])

    first_10 = " ".join(answer.split()[:10])
    if first_10 not in candidates:
        candidates.append(first_10)

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for search_text in candidates:
            search_words = normalize(search_text).split()
            window_size  = max(3, min(len(search_words), 8))

            for page_num, page in enumerate(pdf.pages, start=1):
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False,
                )
                if not words:
                    continue

                page_words_norm = [normalize(w["text"]) for w in words]

                for i in range(len(page_words_norm) - window_size + 1):
                    window = page_words_norm[i: i + window_size]
                    query  = search_words[:window_size]

                    matches     = sum(1 for a, b in zip(window, query) if a == b)
                    match_ratio = matches / window_size

                    if match_ratio >= 0.65:
                        expanded_start = max(0, i - 2)
                        expanded_end   = min(len(words), i + window_size + 2)
                        expanded_words = words[expanded_start:expanded_end]

                        x0 = min(w["x0"]     for w in expanded_words)
                        y0 = min(w["top"]     for w in expanded_words)
                        x1 = max(w["x1"]     for w in expanded_words)
                        y1 = max(w["bottom"] for w in expanded_words)

                        return [{
                            "page":   page_num,
                            "x0":     max(0, x0 - 2),
                            "y0":     max(0, y0 - 2),
                            "x1":     x1 + 2,
                            "y1":     y1 + 2,
                            "width":  page.width,
                            "height": page.height,
                        }]

    return None