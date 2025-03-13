import streamlit as st
import requests
from streamlit_pdf_viewer import pdf_viewer
import tempfile

# Assume backend is running locally on port 8000
BACKEND_URL = "http://localhost:8000"

# Use wide layout
st.set_page_config(layout="wide")

st.title("PDF Extraction & Highlighting")

# File uploader for multiple PDFs
uploaded_pdfs = st.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

# Initialize session state
if "pdf_chunks" not in st.session_state:
    st.session_state.pdf_chunks = {}
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = {}
if "selected_pdf" not in st.session_state:
    st.session_state.selected_pdf = None
if "selected_page" not in st.session_state:
    st.session_state.selected_page = None
if "selected_bbox" not in st.session_state:
    st.session_state.selected_bbox = None
if "selected_row" not in st.session_state:
    st.session_state.selected_row = None

process_button = st.button("Process")

# Store uploaded PDFs in temp files
if uploaded_pdfs:
    for pdf_file in uploaded_pdfs:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_file.getvalue())
            st.session_state[pdf_file.name] = tmp.name  # store path in session

# Process PDFs
if process_button and uploaded_pdfs:
    # Clear old results
    st.session_state.pdf_chunks = {}
    st.session_state.extracted_data = {}
    
    # 1) /reader
    for pdf_file in uploaded_pdfs:
        pdf_name = pdf_file.name
        files = {
            "pdf_file": (pdf_file.name, pdf_file.getvalue(), "application/pdf")
        }
        response = requests.post(f"{BACKEND_URL}/reader", files=files)
        if response.status_code == 200:
            st.session_state.pdf_chunks[pdf_name] = response.json()
        else:
            st.error(f"Failed to process {pdf_name}: {response.text}")
    
    # 2) /extract
    for pdf_file in uploaded_pdfs:
        pdf_name = pdf_file.name
        resp = requests.get(f"{BACKEND_URL}/extract", params={"pdf_name": pdf_name})
        if resp.status_code == 200:
            st.session_state.extracted_data[pdf_name] = resp.json()
        else:
            st.error(f"Failed to extract words for {pdf_name}: {resp.text}")

# If extracted data is available, we'll loop row by row, and for each row:
#   - display the row content (label + PDF buttons) in the left 3/4
#   - reserve the right 1/4 for the pdf_viewer if this row is selected.
if st.session_state.extracted_data:
    pdf_names = list(st.session_state.extracted_data.keys())
    word_count = len(st.session_state.extracted_data[pdf_names[0]])

    st.write("Extracted Results (Click on a content cell to display its PDF on the same row):")

    for i in range(word_count):
        # Create two columns in a 3:1 ratio
        row_cols = st.columns([8, 5])

        with row_cols[0]:
            # Label the row
            st.write(f"Word #{i + 1}")

            # One button per PDF
            for pdf_name in pdf_names:
                chunk_data = st.session_state.extracted_data[pdf_name][i]
                if chunk_data:
                    chunk_content = chunk_data["content"]
                    if st.button(chunk_content, key=f"{pdf_name}-{i}"):
                        # If clicked, store selection in session state
                        st.session_state.selected_pdf = pdf_name
                        st.session_state.selected_page = chunk_data["page_number"]
                        st.session_state.selected_bbox = chunk_data["bbox"]
                        st.session_state.selected_row = i
                else:
                    st.write("---")

        # If this row is selected, show the pdf_viewer in the right 1/4 column
        if (st.session_state.selected_row == i and 
            st.session_state.selected_pdf and
            st.session_state.selected_page is not None and 
            st.session_state.selected_bbox):
            pdf_name = st.session_state.selected_pdf
            pdf_path = st.session_state[pdf_name]
            page = int(st.session_state.selected_page)
            bbox = st.session_state.selected_bbox

            annotations = [{
                "page": page,
                "x": bbox["x1"],
                "y": bbox["y1"],
                "width": bbox["x2"] - bbox["x1"],
                "height": bbox["y2"] - bbox["y1"],
                "color": "red"
            }]

            with row_cols[1]:
                st.write(f"Displaying {pdf_name}, Page {page} with highlight:")
                pages_to_render = [page, page + 1] if page != 0 else [page, page + 1]
                pdf_viewer(
                    input=pdf_path,
                    width="100%",
                    height=800,  # adjust as desired for row height
                    annotations=annotations,
                    pages_to_render=pages_to_render,
                    scroll_to_page=page,
                    render_text=True
                )