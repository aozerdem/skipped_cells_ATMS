import streamlit as st
import openpyxl
import xml.etree.ElementTree as ET
import csv
import re
import tempfile
import os
from io import StringIO

# --- UI Setup ---
st.set_page_config(page_title="Missing Strings Report", page_icon="🔍")

# --- Developer Credit (Top Right) ---
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
                # CORE LOGIC: THE CONSUMPTION MODEL
                # ==========================================================
                
                # Parse the MXLIFF and extract all source strings into a LIST
                tree = ET.parse(mxliff_path)
                root = tree.getroot()
                
                ns = {'xliff': 'urn:oasis:names:tc:xliff:document:1.2'}
                
                mxliff_sources = [] # CHANGED from set() to list()
                for source_node in root.findall('.//xliff:source', ns):
                    text = "".join(source_node.itertext()).strip() 
                    if text:
                        mxliff_sources.append(text)

                # Parse the source XLSX file
                wb = openpyxl.load_workbook(xlsx_path, data_only=True)
                sheet = wb.active 
                
                missing_items = []
                target_columns = ['F', 'G', 'H', 'I', 'J', 'K']
                
                # Iterate through the designated range
                for row in range(2, sheet.max_row + 1):
                    for col_index, col_letter in enumerate(target_columns, start=6):
                        cell = sheet.cell(row=row, column=col_index)
                        
                        if cell.value is not None:
                            cell_text = str(cell.value).strip()
                            
                            if cell_text: 
                                # 1. Exact Match Check: Is it in our available pool?
                                if cell_text in mxliff_sources:
                                    mxliff_sources.remove(cell_text) # Consume it!
                                    
                                else:
                                    # 2. Segmented Check: Can we build it from available segments?
                                    remaining_text = cell_text
                                    segments_to_remove = []
                                    
                                    # Sort CURRENTLY available sources by length (longest first)
                                    current_sorted_sources = sorted(mxliff_sources, key=len, reverse=True)
                                    
                                    for src in current_sorted_sources:
                                        if src in remaining_text:
                                            # Replace only 1 instance to respect exact counts
                                            remaining_text = remaining_text.replace(src, '', 1)
                                            segments_to_remove.append(src)
                                            
                                            # Optimization: Stop checking if we've consumed all text
                                            if len(re.sub(r'[\s\W_]+', '', remaining_text)) == 0:
                                                break
                                    
                                    cleaned_leftover = re.sub(r'[\s\W_]+', '', remaining_text)
                                    
                                    # If letters/numbers are still left, it's missing!
                                    if len(cleaned_leftover) > 0:
                                        missing_items.append({
                                            'Cell': f"{col_letter}{row}",
                                            'Source Text': cell_text
                                        })
                                    else:
                                        # It was perfectly matched via segments! Consume those segments from the pool.
                                        for src in segments_to_remove:
                                            if src in mxliff_sources:
                                                mxliff_sources.remove(src)

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
