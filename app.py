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
st.set_page_config(page_title="Missing Strings Report", page_icon="🔍", layout="wide")

st.markdown(
    """
    <div style='text-align: right; color: gray; font-size: 14px; margin-bottom: -20px;'>
        <i>developed by Ahmet Ozerdem</i>
    </div>
    """, 
    unsafe_allow_html=True
)

st.title("🔍 Missing Strings Report Generator")
st.markdown("Identifies completely skipped cells and improperly segmented (split) strings.")

# --- File Uploaders ---
col1, col2 = st.columns(2)
with col1:
    xlsx_file = st.file_uploader("Step 1: Upload Source XLSX File", type=['xlsx'])
with col2:
    mxliff_file = st.file_uploader("Step 2: Upload Processed MXLIFF File", type=['mxliff'])

if xlsx_file and mxliff_file:
    if st.button("Generate Report", use_container_width=True):
        with st.spinner("Processing files..."):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_xlsx:
                tmp_xlsx.write(xlsx_file.getvalue())
                xlsx_path = tmp_xlsx.name
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mxliff") as tmp_mxliff:
                tmp_mxliff.write(mxliff_file.getvalue())
                mxliff_path = tmp_mxliff.name

            try:
                # ==========================================================
                # CORE LOGIC: NATIVE PARAGRAPH RECONSTRUCTION + BUCKETING
                # ==========================================================
                
                tree = ET.parse(mxliff_path)
                root = tree.getroot()
                
                para_blocks = {}
                
                # 1. Group all MXLIFF segments by their native Memsource Paragraph ID
                for tu in root.iter('{urn:oasis:names:tc:xliff:document:1.2}trans-unit'):
                    para_id = None
                    for key, val in tu.attrib.items():
                        if key.endswith('para-id'):
                            para_id = val
                            break
                            
                    if not para_id:
                        para_id = str(uuid.uuid4())
                        
                    source_node = tu.find('{urn:oasis:names:tc:xliff:document:1.2}source')
                    if source_node is not None:
                        text = "".join(source_node.itertext())
                        if para_id not in para_blocks:
                            para_blocks[para_id] = []
                        para_blocks[para_id].append(text)

                # 2. Create two buckets: Normal Strings and Split Strings
                normal_mxliff_pool = []
                split_mxliff_pool = []
                
                for pid, texts in para_blocks.items():
                    combined_text = "".join(texts)
                    cleaned = re.sub(r'[\s\W_]+', '', combined_text)
                    if cleaned:
                        if len(texts) == 1:
                            normal_mxliff_pool.append(cleaned)
                        else:
                            split_mxliff_pool.append(cleaned)

                # Parse the source XLSX file
                wb = openpyxl.load_workbook(xlsx_path, data_only=True)
                sheet = wb.active 
                
                report_items = []
                target_columns = ['F', 'G', 'H', 'I', 'J', 'K']
                
                # 3. Iterate through Excel and categorize
                for row in range(2, sheet.max_row + 1):
                    for col_index, col_letter in enumerate(target_columns, start=6):
                        cell = sheet.cell(row=row, column=col_index)
                        
                        if cell.value is not None:
                            cell_text = str(cell.value).strip()
                            
                            if cell_text: 
                                cleaned_cell = re.sub(r'[\s\W_]+', '', cell_text)
                                
                                if not cleaned_cell:
                                    continue 
                                    
                                # Check 1: Is it a normal 1:1 match?
                                if cleaned_cell in normal_mxliff_pool:
                                    normal_mxliff_pool.remove(cleaned_cell)
                                    
                                # Check 2: Was it improperly split by ATMS?
                                elif cleaned_cell in split_mxliff_pool:
                                    split_mxliff_pool.remove(cleaned_cell)
                                    report_items.append({
                                        'Cell': f"{col_letter}{row}",
                                        'Status': 'Split String',
                                        'Source Text': cell_text
                                    })
                                    
                                # Check 3: It is genuinely missing
                                else:
                                    report_items.append({
                                        'Cell': f"{col_letter}{row}",
                                        'Status': 'Missing Cell',
                                        'Source Text': cell_text
                                    })

                # ==========================================================
                # CSV OUTPUT, PREVIEW & DOWNLOAD LOGIC
                # ==========================================================
                missing_only = [item for item in report_items if item['Status'] == 'Missing Cell']
                split_only = [item for item in report_items if item['Status'] == 'Split String']
                
                if not report_items:
                    st.success("✅ No hidden strings or segmentation issues found! Everything looks perfect.")
                else:
                    # Metrics Dashboard
                    st.markdown("### 📊 Scan Results")
                    metric_col1, metric_col2 = st.columns(2)
                    metric_col1.metric("Completely Missing Cells", len(missing_only))
                    metric_col2.metric("Improperly Split Strings", len(split_only))
                    
                    st.divider()
                    
                    # UI Consolidated Preview
                    st.markdown("### Consolidated Findings Preview")
                    st.dataframe(report_items, use_container_width=True)
                    
                    # Dynamic File Naming
                    base_name = xlsx_file.name.replace('.xlsx', '')[:15]
                    dynamic_filename = f"LQA_Report_{base_name}.csv"
                    
                    csv_buffer = StringIO()
                    writer = csv.DictWriter(csv_buffer, fieldnames=['Cell', 'Status', 'Source Text'])
                    writer.writeheader()
                    writer.writerows(report_items)
                    
                    st.download_button(
                        label="⬇️ Download Full CSV Report",
                        data=csv_buffer.getvalue(),
                        file_name=dynamic_filename,
                        mime="text/csv",
                        type="primary"
                    )

            except Exception as e:
                st.error(f"An error occurred during processing:\n{e}")
                
            finally:
                if os.path.exists(xlsx_path):
                    os.remove(xlsx_path)
                if os.path.exists(mxliff_path):
                    os.remove(mxliff_path)
