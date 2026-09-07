# pdf_qna_engine/llm.py
from typing import List, Tuple
import requests
import os

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

def get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("Set your GROQ_API_KEY in environment variables.")
    return key

def ask_model(
    question: str,
    contexts: List[str],
    chat_history: List[dict] = None,
    full_text: str = None,
) -> Tuple[str, float]:
    api_key = get_api_key()

    MAX_CHARS = 12000
    if full_text and len(full_text) <= MAX_CHARS:
        context = full_text
    else:
        context = "\n\n".join(contexts[:2])

    messages = [
        {"role": "system", "content": f"You are a helpful assistant answering questions based on the PDF content below.\n\nContext:\n{context}"}
    ]

    if chat_history:
        for entry in chat_history[-4:]:
            messages.append({"role": "user", "content": entry["question"]})
            messages.append({"role": "assistant", "content": entry["answer"]})

    messages.append({"role": "user", "content": question})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 300,
        "temperature": 0.3,
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=180)
        response.raise_for_status()
        data = response.json()

        answer = data["choices"][0]["message"]["content"].strip()
        confidence = 0.0 if "does not contain" in answer.lower() else 90.0
        return answer if answer else "No answer generated.", confidence

    except requests.exceptions.Timeout:
        return "Request timed out. Try reducing context size.", 0.0
    except requests.exceptions.RequestException as e:
        return f"API error: {str(e)}", 0.0