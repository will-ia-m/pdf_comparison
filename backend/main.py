import os
import uuid
import io
import pdfplumber
from fastapi import FastAPI, File, UploadFile, Body
from fastapi.responses import JSONResponse, StreamingResponse
import yaml
from typing import List, Dict, Optional
import pandas as pd
from io import BytesIO

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
    Chunking: 21 lines at a time, with a newline after every 7 lines inside that chunk.
    """
    # If already in cache, return
    if pdf_name in PDF_CACHE:
        return PDF_CACHE[pdf_name]
    
    chunks = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            lines = page.extract_words() or []
            for i in range(0, len(lines), 21):
                block = lines[i : i + 21]
                if not block:
                    continue

                # Build content with a '\n' after every 7 lines
                # We'll still join line segments themselves with a space
                chunk_lines = []
                for idx, item in enumerate(block):
                    chunk_lines.append(item["text"])
                    # Insert a newline after every 7 lines, if not at end
                    if (idx + 1) % 7 == 0 and (idx + 1) < len(block):
                        chunk_lines.append("\n")

                content = " ".join(chunk_lines)

                # Merge bounding boxes:
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
    PDF_CACHE[pdf_name] = chunks
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
    The index of the chunk in the returned list corresponds
    to the index of each word in WORDS_TO_EXTRACT.
    """
    chunks = PDF_CACHE.get(pdf_name, [])
    result = []
    
    for word in WORDS_TO_EXTRACT:
        # Find the first chunk that includes the word (case-insensitive)
        match_chunk = None
        lower_word = word.lower()
        for chunk in chunks:
            # remove double-spaces for a simpler substring match
            if lower_word in chunk["content"].lower().replace('  ',' '):
                match_chunk = chunk
                break
        result.append(match_chunk)
    
    return JSONResponse(result)


@app.get("/words")
def get_words():
    """
    Return the list of words to extract from config.yaml
    """
    return JSONResponse(WORDS_TO_EXTRACT)


@app.post("/export_excel")
def export_excel(data: List[Dict]):
    """
    Receive a list of {word, pdf_name, content, page_number, bbox} 
    and produce an Excel file containing these records.
    Return the Excel file as a streaming response.
    """
    # Convert incoming data to a DataFrame
    df = pd.DataFrame(data)
    # Reorder columns if desired, or keep them as is
    # e.g. columns = ["word", "pdf_name", "content", "page_number", "bbox"]
    # but let's just keep the same order that arrived

    # Create an Excel in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="ExtractedData")

    output.seek(0)

    headers = {
        'Content-Disposition': 'attachment; filename="modified_data.xlsx"'
    }
    return StreamingResponse(output, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)