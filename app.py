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
st.title("🔍 Missing Strings Report Generator")

# --- File Uploaders ---
st.markdown("### Step 1: Upload Source XLSX")
xlsx_file = st.file_uploader("Select Source XLSX File", type=['xlsx'])

st.markdown("### Step 2: Upload Processed MXLIFF")
mxliff_file = st.file_uploader("Select Processed MXLIFF File", type=['mxliff'])

if xlsx_file and mxliff_file:
    if st.button("Generate Report"):
        with st.spinner("Processing files..."):
            
            # 1. Create temporary physical files so openpyxl behaves exactly like the offline script
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_xlsx:
                tmp_xlsx.write(xlsx_file.getvalue())
                xlsx_path = tmp_xlsx.name
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mxliff") as tmp_mxliff:
                tmp_mxliff.write(mxliff_file.getvalue())
                mxliff_path = tmp_mxliff.name

            try:
                # ==========================================================
                # CORE LOGIC 
                # ==========================================================
                
                # Parse the MXLIFF and extract all source strings
                tree = ET.parse(mxliff_path)
                root = tree.getroot()
                
                # ATMS MXLIFFs use the standard XLIFF 1.2 namespace
                ns = {'xliff': 'urn:oasis:names:tc:xliff:document:1.2'}
                
                mxliff_sources = set()
                for source_node in root.findall('.//xliff:source', ns):
                    text = "".join(source_node.itertext()).strip() 
                    if text:
                        mxliff_sources.add(text)

                # Sort MXLIFF sources by length (longest first) to ensure safe subtraction
                sorted_sources = sorted(mxliff_sources, key=len, reverse=True)

                # Parse the source XLSX file
                wb = openpyxl.load_workbook(xlsx_path, data_only=True)
                sheet = wb.active 
                
                missing_items = []
                target_columns = ['F', 'G', 'H', 'I', 'J', 'K']
                
                # Iterate through the designated range (Row 2 onwards, Cols F-K)
                for row in range(2, sheet.max_row + 1):
                    for col_index, col_letter in enumerate(target_columns, start=6):
                        cell = sheet.cell(row=row, column=col_index)
                        
                        if cell.value is not None:
                            cell_text = str(cell.value).strip()
                            
                            if cell_text: 
                                # First check: Is the exact full string in the MXLIFF?
                                if cell_text not in mxliff_sources:
                                    
                                    # WORKAROUND: Check if the string was segmented by punctuation
                                    remaining_text = cell_text
                                    for src in sorted_sources:
                                        if src in remaining_text:
                                            remaining_text = remaining_text.replace(src, '')
                                    
                                    # Remove all whitespace, punctuation, and special symbols from leftovers
                                    cleaned_leftover = re.sub(r'[\s\W_]+', '', remaining_text)
                                    
                                    # If there are still letters/numbers left, it wasn't just segmented—it's hidden!
                                    if len(cleaned_leftover) > 0:
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
                    
                    # --- NEW: UI Preview ---
                    st.markdown("### Missing Cells Preview")
                    st.dataframe(missing_items, use_container_width=True)
                    
                    # --- NEW: Dynamic File Naming ---
                    # Strip the .xlsx extension and take the first 15 characters
                    base_name = xlsx_file.name.replace('.xlsx', '')[:15]
                    dynamic_filename = f"missing_cells_{base_name}.csv"
                    
                    # Write results to a memory buffer for the download button
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
                # Clean up the temporary files from the Streamlit server
                if os.path.exists(xlsx_path):
                    os.remove(xlsx_path)
                if os.path.exists(mxliff_path):
                    os.remove(mxliff_path)
