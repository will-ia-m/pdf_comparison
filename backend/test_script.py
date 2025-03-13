import sys
import os
import uuid
import pdfplumber
import yaml

# Optional: Adjust the import path depending on your folder structure
from main import parse_pdf, PDF_CACHE, WORDS_TO_EXTRACT


def test_parse_pdf(pdf_path: str):
    """
    Test the parse_pdf function outside of the API context,
    then check the first match for each word to extract.
    """
    if not os.path.isfile(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    # Read PDF bytes
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pdf_name = os.path.basename(pdf_path)

    # Use the same parse_pdf function from main
    chunks = parse_pdf(pdf_bytes, pdf_name)
    print(f"Found {len(chunks)} chunks in {pdf_name}\n")

    # Print a sample of the extracted chunks (in practice you could examine them all)
    sample_count = min(5, len(chunks))
    for i in range(sample_count):
        print(f"Sample chunk #{i+1}: {chunks[i]}")

    # Attempt to match the first chunk containing each word in WORDS_TO_EXTRACT (case-insensitive)
    results = []
    for word in WORDS_TO_EXTRACT:
        match_chunk = None
        for chunk in chunks:
            if word.lower() in chunk["content"].lower().replace('  ',' '):
                match_chunk = chunk
                break
        results.append((word, match_chunk))
    
    print("\nFirst match result for each word in config:")
    for word, chunk in results:
        if chunk:
            print(f"Word: '{word}' matches chunk content: '{chunk['content']}' (page {chunk['page_number']})")
        else:
            print(f"Word: '{word}' not found in any chunk.")


def main(pdf_path):
    test_parse_pdf(pdf_path)


if __name__ == "__main__":
    pdf_path = "/home/willip/Downloads/exemple_paper/2006.14615v2.pdf"
    main(pdf_path)
