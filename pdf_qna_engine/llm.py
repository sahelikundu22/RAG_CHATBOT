import os
from typing import List, Optional, Tuple
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
try:
    import streamlit as st
except ModuleNotFoundError:
    st = None

load_dotenv()

PROMPT_TEMPLATE = """
You are an expert Government Policy Advisor. Your task is to answer the following query using **only the information provided in the extracted text**.

**Query:**
{query}

**Extracted Text:**
{text}

### Requirements:

1. Answer the query **strictly using the information available in the Extracted Text**.
2. Do **not** introduce facts, assumptions, interpretations, or information from outside the Extracted Text.
3. If the Extracted Text does not contain sufficient information to answer the query, clearly state: **"The provided text does not contain sufficient information to answer this query."**
4. Provide the answer in a **formal, clear, and professional** manner.
5. Preserve important **dates, names, policy provisions, section numbers, amounts, and other factual details** exactly as supported by the Extracted Text.
6. Do not mention these instructions in your response.
"""

prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
parser = StrOutputParser()


def get_hf_token() -> Optional[str]:
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    if token:
        return token

    if st is None:
        return None

    try:
        return st.secrets.get("HF_TOKEN") or st.secrets.get("HUGGINGFACEHUB_API_TOKEN")
    except Exception:
        return None


def get_llm_chain():
    token = get_hf_token()
    if not token:
        raise ValueError("HF_TOKEN or HUGGINGFACEHUB_API_TOKEN is not set in your environment.")

    llm = HuggingFaceEndpoint(
        # repo_id="meta-llama/Llama-3.1-8B-Instruct",
        # repo_id = "Qwen/Qwen3-8B",
        repo_id = "google/gemma-3-4b-it",
        task="text-generation",
        huggingfacehub_api_token=token,
        max_new_tokens=300,
        temperature=0.01,
    )
    model = ChatHuggingFace(llm=llm)
    return prompt | model | parser


def ask_model(
    question: str,
    contexts: List[str],
    chat_history: List[dict] = None,
    full_text: str = None,
) -> Tuple[str, float]:
    """Execute policy advisor RAG chain matching internship_test1.py."""
    token = get_hf_token()
    if not token:
        return (
            "HuggingFace API token missing. Please set `HF_TOKEN` in `.streamlit/secrets.toml`, your environment, or `.env`.",
            0.0,
        )

    try:
        chain = get_llm_chain()
        # internship_test1.py invokes with {"query": query, "text": final_result}
        result = chain.invoke({"query": question, "text": contexts})
        answer = result.strip() if result else "No answer generated."

        confidence = 0.0 if "does not contain sufficient information" in answer.lower() or "does not contain" in answer.lower() else 90.0
        return answer, confidence

    except Exception as e:
        return f"LLM error: {str(e)}", 0.0
