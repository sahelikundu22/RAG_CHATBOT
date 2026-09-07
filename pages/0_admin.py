import streamlit as st

from pdf_qna_engine.library import available_pdfs, cache_dir_for, get_indexed_pdf, is_index_cached

st.title("Admin")

pdfs = available_pdfs()

if not pdfs:
    st.warning("No PDFs found in the documents folder.")
else:
    st.subheader("Documents")

    for name, path in pdfs.items():
        with st.container(border=True):
            st.write(name)
            st.caption(str(path))
            st.caption(f"Index: {cache_dir_for(name)}")
            st.write("Status:", "Cached on disk" if is_index_cached(name) else "Not prepared")

            if st.button("Prepare index", key=f"prepare-{name}"):
                indexed_pdf = get_indexed_pdf(name)
                st.success(f"Ready: {len(indexed_pdf.chunks)} chunks indexed and saved.")

    if st.button("Prepare all PDFs"):
        total_chunks = 0
        for name in pdfs:
            total_chunks += len(get_indexed_pdf(name).chunks)
        st.success(f"Prepared {len(pdfs)} PDF(s), {total_chunks} total chunks saved.")
