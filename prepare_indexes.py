from pdf_qna_engine.library import available_pdfs, cache_dir_for, get_indexed_pdf


def main() -> None:
    pdfs = available_pdfs()
    if not pdfs:
        print("No built-in PDFs found.")
        return

    for name in pdfs:
        indexed_pdf = get_indexed_pdf(name)
        print(f"{name}: {len(indexed_pdf.chunks)} chunks")
        print(f"Saved to: {cache_dir_for(name)}")


if __name__ == "__main__":
    main()
