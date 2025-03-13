import streamlit as st
import requests
from streamlit_pdf_viewer import pdf_viewer
import tempfile

# Assume backend is running locally on port 8000
BACKEND_URL = "http://localhost:8000"

st.set_page_config(layout="wide")  # Utilize the full width of the page
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

process_button = st.button("Process")



# After the file is uploaded:
if uploaded_pdfs:
    for pdf_file in uploaded_pdfs:
        # Create a temporary file to store the PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_file.getvalue())
            # Save the temporary file path to session state for later use
            st.session_state[pdf_file.name] = tmp.name


if process_button and uploaded_pdfs:
    # Clear old results
    st.session_state.pdf_chunks = {}
    st.session_state.extracted_data = {}
    
    for pdf_file in uploaded_pdfs:
        pdf_name = pdf_file.name
        
        # Send the PDF to the backend's /reader route
        files = {
            "pdf_file": (pdf_file.name, pdf_file.getvalue(), "application/pdf")
        }
        response = requests.post(f"{BACKEND_URL}/reader", files=files)
        if response.status_code == 200:
            st.session_state.pdf_chunks[pdf_name] = response.json()
        else:
            st.error(f"Failed to process {pdf_name}: {response.text}")
    
    # Now that we've cached each PDF, call /extract for each
    for pdf_file in uploaded_pdfs:
        pdf_name = pdf_file.name
        resp = requests.get(f"{BACKEND_URL}/extract", params={"pdf_name": pdf_name})
        if resp.status_code == 200:
            st.session_state.extracted_data[pdf_name] = resp.json()
        else:
            st.error(f"Failed to extract words for {pdf_name}: {resp.text}")

# Display table and PDF viewer if we have extracted data
if st.session_state.extracted_data:
    # Determine the words from the first PDF's result
    sample_pdf = list(st.session_state.extracted_data.keys())[0]
    word_count = len(st.session_state.extracted_data[sample_pdf])
    
    # Prepare table data
    pdf_names = list(st.session_state.extracted_data.keys())
    table_data = []
    for i in range(word_count):
        row = [f"Word #{i+1}"]
        for pdf_name in pdf_names:
            chunk = st.session_state.extracted_data[pdf_name][i]
            row.append(chunk["content"] if chunk else "---")
        table_data.append(row)
    
    # Layout: Table on the left, PDF viewer on the right
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.write("Extracted Results (Click a cell to highlight):")
        for row in table_data:
            st.write("---")
            col1, *other_cols = st.columns(len(row))
            col1.write(row[0])  # word
            for idx, cell in enumerate(other_cols):
                pdf_name = pdf_names[idx]
                chunk_index = table_data.index(row)
                chunk_data = st.session_state.extracted_data[pdf_name][chunk_index]
                if chunk_data:
                    if st.button(f"{row[0]}: {pdf_name}", key=f"{row[0]}-{pdf_name}"):
                        # Set session state for selected PDF, page, and bbox
                        st.session_state.selected_pdf = pdf_name
                        st.session_state.selected_page = chunk_data["page_number"]
                        st.session_state.selected_bbox = chunk_data["bbox"]
                        st.success(
                            f"Selected chunk from {pdf_name} on page {chunk_data['page_number']} with bbox={chunk_data['bbox']}"
                        )
    
    with col2:
        if st.session_state.selected_pdf:
            # Use the stored temporary file path
            pdf_path = st.session_state[st.session_state.selected_pdf]
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
            
            st.write(f"Displaying {st.session_state.selected_pdf}, Page {page} with highlight:")
            pages_to_render = [p for p in ([page, page + 1] if page != 0 else [page, page + 1])]
            pdf_viewer(
                input=pdf_path,
                width="100%",
                height=800,
                annotations=annotations,
                pages_to_render = pages_to_render,
                scroll_to_page=page,
                render_text=True
            )
