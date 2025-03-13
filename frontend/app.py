import streamlit as st
import requests
from streamlit_pdf_viewer import pdf_viewer
import tempfile
import json

# Assume backend is running locally on port 8000
BACKEND_URL = "http://localhost:8000"

# Use wide layout
st.set_page_config(layout="wide")

st.title("Termsheet cross-evaluation (with editing & Excel export)")

# -- SESSION STATE INIT --
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
if "word_list" not in st.session_state:
    # fetch from backend
    response = requests.get(f"{BACKEND_URL}/words")
    if response.status_code == 200:
        st.session_state.word_list = response.json()
    else:
        st.session_state.word_list = []

# File uploader for multiple PDFs
uploaded_pdfs = st.file_uploader(
    "Upload PDF files of termsheets",
    type=["pdf"],
    accept_multiple_files=True
)

# Store uploaded PDFs in temp files for reference
if uploaded_pdfs:
    for pdf_file in uploaded_pdfs:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_file.getvalue())
            st.session_state[pdf_file.name] = tmp.name  # store path in session

process_button = st.button("Extract key elements from selected termsheets")

# Process PDFs
if process_button and uploaded_pdfs:
    # Clear old results
    st.session_state.pdf_chunks = {}
    st.session_state.extracted_data = {}
    
    # 1) Call /reader for each uploaded PDF
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
    
    # 2) Call /extract for each PDF
    for pdf_file in uploaded_pdfs:
        pdf_name = pdf_file.name
        resp = requests.get(f"{BACKEND_URL}/extract", params={"pdf_name": pdf_name})
        if resp.status_code == 200:
            st.session_state.extracted_data[pdf_name] = resp.json()
        else:
            st.error(f"Failed to extract words for {pdf_name}: {resp.text}")

# Display extracted data if available
if st.session_state.extracted_data:
    pdf_names = list(st.session_state.extracted_data.keys())
    words = st.session_state.word_list  # the order should match backend's result
    word_count = len(words)

    if word_count > 0:
        st.write("Extracted Results (You can edit the text areas, then click 'p' to preview the PDF chunk):")

        for i in range(word_count):
            # Create row with 3 columns: left (word + text areas), middle (p buttons), right (PDF viewer)
            row_cols = st.columns([7, 1, 5])

            with row_cols[0]:
                # Show the word in large bold text
                st.markdown(
                    f"<span style='font-size: 24px; font-weight: bold;'>{words[i]}</span>",
                    unsafe_allow_html=True
                )
                # For each PDF, show an editable text area
                for pdf_name in pdf_names:
                    chunk_data = st.session_state.extracted_data[pdf_name][i]
                    if chunk_data:
                        st.markdown(f"• {pdf_name}")
                        default_text = chunk_data["content"]
                        # Use a text_area for multi-line editing
                        updated_text = st.text_area(
                            label=f"{pdf_name} - {words[i]}",
                            value=default_text,
                            key=f"txt_{pdf_name}_{i}",
                            height=100
                        )

            with row_cols[1]:
                # Place the "p" buttons for each PDF chunk
                for pdf_name in pdf_names:
                    chunk_data = st.session_state.extracted_data[pdf_name][i]
                    if chunk_data:
                        if st.button("p", key=f"pb_{pdf_name}_{i}"):
                            st.session_state.selected_pdf = pdf_name
                            st.session_state.selected_page = chunk_data["page_number"]
                            st.session_state.selected_bbox = chunk_data["bbox"]
                            st.session_state.selected_row = i

            # If this row is selected, show the pdf_viewer in the right column
            with row_cols[2]:
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

                    st.write(f"Displaying {pdf_name}, Page {page} with highlight:")
                    pages_to_render = [page, page + 1] if page != 0 else [page, page + 1]
                    pdf_viewer(
                        input=pdf_path,
                        width="100%",
                        height=900,  # adjust as desired
                        annotations=annotations,
                        pages_to_render=pages_to_render,
                        scroll_to_page=page,
                        render_text=True,
                        annotation_outline_size=3
                    )

        # -- Export to Excel --
        st.write("---")
        st.write("When satisfied with your edits, export all data to Excel:")

        if st.button("Export to Excel"):
            # Gather updated data for export
            # We'll build a list of dicts: each row has "word", "pdf_name", "content", "page_number", "bbox"
            final_data_for_export = []
            for i, word in enumerate(words):
                for pdf_name in pdf_names:
                    chunk_data = st.session_state.extracted_data[pdf_name][i]
                    if chunk_data:
                        # use updated text
                        updated_content = st.session_state.get(f"txt_{pdf_name}_{i}", chunk_data["content"])
                        final_data_for_export.append({
                            "word": word,
                            "pdf_name": pdf_name,
                            "content": updated_content,
                            "page_number": chunk_data["page_number"],
                            "bbox": chunk_data["bbox"]
                        })
            # Call the new backend route
            export_response = requests.post(
                f"{BACKEND_URL}/export_excel",
                json=final_data_for_export
            )
            if export_response.status_code == 200:
                # Provide a download button in Streamlit
                st.download_button(
                    label="Download Excel",
                    data=export_response.content,
                    file_name="modified_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error(f"Export failed: {export_response.text}")

    else:
        st.write("No words found in config or no words configured to extract.")