import streamlit as st
import openpyxl
import xml.etree.ElementTree as ET
import csv
import re
import tempfile
import os
import uuid
from io import StringIO

# --- UI Setup ---
st.set_page_config(page_title="Missing Strings Report", page_icon="🔍")

st.markdown(
    """
    <div style='text-align: right; color: gray; font-size: 14px; margin-bottom: -20px;'>
        <i>developed for Acclaro</i>
    </div>
    """, 
    unsafe_allow_html=True
)

st.title("🔍 Missing Strings Report Generator")

# --- File Uploaders ---
st.markdown("### Step 1: Upload Source XLSX")
xlsx_file = st.file_uploader("Select Source XLSX File", type=['xlsx'])

st.markdown("### Step 2: Upload Processed MXLIFF")
mxliff_file = st.file_uploader("Select Processed MXLIFF File", type=['mxliff'])

if xlsx_file and mxliff_file:
    if st.button("Generate Report"):
        with st.spinner("Processing files..."):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_xlsx:
                tmp_xlsx.write(xlsx_file.getvalue())
                xlsx_path = tmp_xlsx.name
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mxliff") as tmp_mxliff:
                tmp_mxliff.write(mxliff_file.getvalue())
                mxliff_path = tmp_mxliff.name

            try:
                # ==========================================================
                # CORE LOGIC: NATIVE PARAGRAPH RECONSTRUCTION
                # ==========================================================
                
                tree = ET.parse(mxliff_path)
                root = tree.getroot()
                
                para_blocks = {}
                
                # 1. Group all MXLIFF segments by their native Memsource Paragraph ID
                for tu in root.iter('{urn:oasis:names:tc:xliff:document:1.2}trans-unit'):
                    para_id = None
                    # Safely find the para-id ignoring strict namespace mapping
                    for key, val in tu.attrib.items():
                        if key.endswith('para-id'):
                            para_id = val
                            break
                            
                    # If no para-id exists, assign a unique one so it doesn't falsely merge
                    if not para_id:
                        para_id = str(uuid.uuid4())
                        
                    source_node = tu.find('{urn:oasis:names:tc:xliff:document:1.2}source')
                    if source_node is not None:
                        text = "".join(source_node.itertext())
                        if para_id not in para_blocks:
                            para_blocks[para_id] = []
                        para_blocks[para_id].append(text)

                # 2. Compile the MXLIFF pool by joining segments of the same paragraph 
                #    and stripping all whitespace/punctuation for a bulletproof comparison.
                cleaned_mxliff_pool = []
                for pid, texts in para_blocks.items():
                    combined_text = "".join(texts)
                    cleaned = re.sub(r'[\s\W_]+', '', combined_text)
                    if cleaned:
                        cleaned_mxliff_pool.append(cleaned)

                # Parse the source XLSX file
                wb = openpyxl.load_workbook(xlsx_path, data_only=True)
                sheet = wb.active 
                
                missing_items = []
                target_columns = ['F', 'G', 'H', 'I', 'J', 'K']
                
                # 3. Iterate through Excel and verify against the reconstructed pool
                for row in range(2, sheet.max_row + 1):
                    for col_index, col_letter in enumerate(target_columns, start=6):
                        cell = sheet.cell(row=row, column=col_index)
                        
                        if cell.value is not None:
                            cell_text = str(cell.value).strip()
                            
                            if cell_text: 
                                # Strip all whitespace/punctuation from the Excel cell too
                                cleaned_cell = re.sub(r'[\s\W_]+', '', cell_text)
                                
                                if not cleaned_cell:
                                    continue # Ignore cells that are purely punctuation
                                    
                                if cleaned_cell in cleaned_mxliff_pool:
                                    # Consume it so duplicates aren't falsely validated
                                    cleaned_mxliff_pool.remove(cleaned_cell)
                                else:
                                    # It's genuinely missing!
                                    missing_items.append({
                                        'Cell': f"{col_letter}{row}",
                                        'Source Text': cell_text
                                    })

                # ==========================================================
                # CSV OUTPUT, PREVIEW & DOWNLOAD LOGIC
                # ==========================================================
                if not missing_items:
                    st.success("✅ No hidden or missing strings found! Everything looks good.")
                else:
                    st.warning(f"⚠️ Found {len(missing_items)} hidden strings.")
                    
                    st.markdown("### Missing Cells Preview")
                    st.dataframe(missing_items, use_container_width=True)
                    
                    base_name = xlsx_file.name.replace('.xlsx', '')[:15]
                    dynamic_filename = f"missing_cells_{base_name}.csv"
                    
                    csv_buffer = StringIO()
                    writer = csv.DictWriter(csv_buffer, fieldnames=['Cell', 'Source Text'])
                    writer.writeheader()
                    writer.writerows(missing_items)
                    
                    st.download_button(
                        label="⬇️ Download CSV Report",
                        data=csv_buffer.getvalue(),
                        file_name=dynamic_filename,
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"An error occurred during processing:\n{e}")
                
            finally:
                if os.path.exists(xlsx_path):
                    os.remove(xlsx_path)
                if os.path.exists(mxliff_path):
                    os.remove(mxliff_path)
