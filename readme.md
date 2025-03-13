# PDF Extraction & Highlighting Example

This repository demonstrates a two-part project:

1. A FastAPI backend (in Python) that:
   - Accepts a PDF file via POST (/reader).
   - Extracts lines of text (chunks) from each page along with bounding boxes.
   - Caches the chunks in memory.
   - Provides a main route (/extract) that reads a YAML configuration containing 
     a list of words to extract and returns, for each word, the first chunk containing that word.

2. A Streamlit frontend that:
   - Lets the user upload multiple PDFs.
   - Calls the backend for each PDF to retrieve the chunk data.
   - Displays a table with (N + 1) columns: The first column is the list of words 
     from the YAML config, and each additional column displays the first matching chunk 
     content from each PDF.
   - When a particular chunk cell is clicked, it displays the corresponding PDF page 
     with a highlighted bounding box (demonstrated as a placeholder in this example).

## Getting started

### Backend
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the service:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Frontend
1. Open a new terminal or deactivate from the backend environment.  
2. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
3. Create a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

### Usage
1. In your browser, open Streamlit at http://localhost:8501 (default Streamlit port).  
2. Drag and drop multiple PDF files or click to select them.  
3. Press the "Process" button. The backend will extract the PDF text chunks.  
4. A table will appear with the list of words (from the backend’s config.yaml) in the first column  
   and the found text chunk for each PDF in subsequent columns.  
5. Click a cell to (optionally) display the PDF page with a rectangle highlight around the extracted bounding box.
