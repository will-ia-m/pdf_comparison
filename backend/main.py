import os
import uuid
import io
import pdfplumber
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import yaml
from typing import List, Dict, Optional

app = FastAPI()

# Simple in-memory cache: { "filename": [ {chunk_info}, ... ] }
PDF_CACHE = {}

# Read config.yaml at startup to get words to extract
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

WORDS_TO_EXTRACT = config.get("word_to_extract", [])


def parse_pdf(file_bytes: bytes, pdf_name: str):
    """
    Parse the PDF using pdfplumber and create chunk data with
    text, bounding box, page number, and a uuid.
    """
    # If already in cache, return
    if pdf_name in PDF_CACHE:
        return PDF_CACHE[pdf_name]
    
    chunks = []
    if 1:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                lines = page.extract_words() or []
                # Create blocks of 100 lines
                for i in range(0, len(lines), 101):
                    block = lines[i : i + 101]
                    if not block:
                        continue
                    
                    # Concatenate the text from each line, separated by spaces
                    content = " ".join([item["text"] for item in block])
                    
                    # Merge bounding boxes:
                    # x1, y1 = min of top-left corners
                    # x2, y2 = max of bottom-right corners
                    x1 = min(item["x0"] for item in block)
                    y1 = min(item["top"] for item in block)
                    x2 = max(item["x1"] for item in block)
                    y2 = max(item["bottom"] for item in block)
                    
                    chunk_uuid = str(uuid.uuid4())
                    chunk = {
                        "content": content,
                        "bbox": {
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2
                        },
                        "uuid": chunk_uuid,
                        "page_number": page_number
                    }
                    chunks.append(chunk)
        # Store in cache
        PDF_CACHE[pdf_name] = chunks
    # except Exception as e:
    #     print(f"Error parsing PDF: {e}")
    #     return []
    return chunks


@app.post("/reader")
async def reader_route(pdf_file: UploadFile = File(...)):
    """
    Receive a PDF file, extract its text lines (chunks) along with bounding box info.
    Return the extracted data as JSON.
    """
    pdf_name = pdf_file.filename
    file_bytes = await pdf_file.read()
    chunks = parse_pdf(file_bytes, pdf_name)
    return JSONResponse(chunks)


@app.get("/extract")
def extract_words(pdf_name: str):
    """
    For a given PDF name (already uploaded / cached),
    return a list of chunks that correspond to the first chunk
    containing each word (in WORDS_TO_EXTRACT).
    """
    chunks = PDF_CACHE.get(pdf_name, [])
    result = []
    
    for word in WORDS_TO_EXTRACT:
        # Find the first chunk that includes the word (case-insensitive)
        match_chunk = None
        lower_word = word.lower()
        for chunk in chunks:
            if lower_word in chunk["content"].lower().replace('  ',' '):
                match_chunk = chunk
                break
        result.append(match_chunk)
    
    return JSONResponse(result)
