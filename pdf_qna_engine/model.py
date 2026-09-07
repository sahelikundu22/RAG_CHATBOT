try:
    import streamlit as st
except ModuleNotFoundError:
    st = None

from langchain_huggingface import HuggingFaceEmbeddings


def _get_cache_decorator():
    if st is not None:
        return st.cache_resource
    return lambda fn: fn


@_get_cache_decorator()
def load_embedding_model(model_name: str = "BAAI/bge-small-en-v1.5") -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=model_name)
