import streamlit as st
from streamlit_pdf_viewer import pdf_viewer
from pdf_qna_engine.highlighter import find_highlight_coords
from pdf_qna_engine.library import available_pdfs, get_indexed_pdf
from pdf_qna_engine.llm import ask_model
from pdf_qna_engine.processor import extract_text, process_text
from pdf_qna_engine.search import build_faiss_index, search_chunks

st.title("PDF Q&A")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "highlights" not in st.session_state:
    st.session_state.highlights = None

built_in_pdfs = available_pdfs()
selected_pdf = None
uploaded_file = None

if built_in_pdfs:
    selected_name = st.sidebar.selectbox("Document", list(built_in_pdfs.keys()))
    selected_pdf = get_indexed_pdf(selected_name)
    st.sidebar.caption("This document is loaded from the saved index after the first run.")

    # with st.sidebar.expander("Use a different PDF"):
    #     uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
else:
    st.sidebar.warning("No PDFs found in the documents folder.")
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

if selected_pdf or uploaded_file:
    pdf_bytes = selected_pdf.pdf_bytes if selected_pdf else uploaded_file.getvalue()

    col_pdf, col_chat = st.columns([1.2, 1])

    with col_pdf:
        st.subheader("PDF Preview")

        highlights = st.session_state.get("highlights")
        if highlights:
            h = highlights[0]
            annotations = [{
                "page": h["page"],
                "x": h["x0"],
                "y": h["y0"],
                "width": h["x1"] - h["x0"],
                "height": h["y1"] - h["y0"],
                "color": "yellow",
            }]
            pdf_viewer(
                input=pdf_bytes,
                width=500,
                height=700,
                annotations=annotations,
                scroll_to_page=h["page"],
            )
            st.caption(f"Answer highlighted on page {h['page']}")
        else:
            pdf_viewer(input=pdf_bytes, width=500, height=700)

    with col_chat:
        st.subheader("Chat")

        file_id = (
            str(selected_pdf.path) + str(selected_pdf.path.stat().st_mtime)
            if selected_pdf
            else uploaded_file.name + str(len(pdf_bytes))
        )
        if st.session_state.get("file_id") != file_id:
            st.session_state.chat_history = []
            st.session_state.highlights = None

            if selected_pdf:
                raw_text = selected_pdf.raw_text
                chunks = selected_pdf.chunks
                embeddings = selected_pdf.embeddings
            else:
                with st.spinner("Processing PDF..."):
                    raw_text = extract_text(uploaded_file)
                    chunks, embeddings = process_text(raw_text)

            persist_dir = selected_pdf.cache_dir if selected_pdf else None
            build_faiss_index(
                chunks,
                embeddings,
                persist_dir=persist_dir,
                collection_key=file_id,
            )
            st.session_state.raw_text = raw_text
            st.session_state.chunks = chunks
            st.session_state.embeddings = embeddings
            st.session_state.persist_dir = str(persist_dir) if persist_dir else None
            st.session_state.file_id = file_id
            st.session_state.total_chunks = len(chunks)

            st.success(f"PDF ready: {len(chunks)} chunks indexed.")
        else:
            build_faiss_index(
                st.session_state.get("chunks", []),
                st.session_state.get("embeddings"),
                persist_dir=st.session_state.get("persist_dir"),
                collection_key=file_id,
            )
            st.info(f"Ready: {st.session_state.get('total_chunks', 0)} chunks indexed.")

        chat_container = st.container(height=500)
        with chat_container:
            if not st.session_state.chat_history:
                st.caption("Ask a question about the PDF to get started.")
            else:
                for entry in st.session_state.chat_history:
                    with st.chat_message("user"):
                        st.write(entry["question"])
                    with st.chat_message("assistant"):
                        st.write(entry["answer"])
                        st.caption(f"Confidence: {entry['confidence']}%")
                        if entry.get("highlight_page"):
                            st.caption(f"Highlighted on page {entry['highlight_page']}")

        question = st.chat_input("Ask a question about the PDF...")

        if question:
            if "chunks" not in st.session_state:
                st.warning("PDF is still processing. Please wait.")
            else:
                with st.spinner("Thinking..."):
                    results, _ = search_chunks(question, top_k=2)
                    answer, confidence = ask_model(
                        question,
                        results,
                        chat_history=st.session_state.chat_history,
                        full_text=st.session_state.get("raw_text"),
                    )
                    highlights = find_highlight_coords(pdf_bytes, answer, contexts=results)

                st.session_state.highlights = highlights
                st.session_state.chat_history.append({
                    "question": question,
                    "answer": answer,
                    "confidence": confidence,
                    "highlight_page": highlights[0]["page"] if highlights else None,
                })
                st.rerun()

        if st.session_state.chat_history:
            if st.button("Clear Chat History"):
                st.session_state.chat_history = []
                st.session_state.highlights = None
                st.rerun()
else:
    st.info("Upload a PDF to get started.")
