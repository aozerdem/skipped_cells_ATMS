import streamlit as st
import openpyxl
import xml.etree.ElementTree as ET
import csv
import re
import tempfile
import os
from io import StringIO

# --- Page Config ---
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
            
            # 1. Create temporary physical files on the server
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_xlsx:
                tmp_xlsx.write(xlsx_file.getvalue())
                xlsx_path = tmp_xlsx.name
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mxliff") as tmp_mxliff:
                tmp_mxliff.write(mxliff_file.getvalue())
                mxliff_path = tmp_mxliff.name

            try:
                # 2. Pass the physical file paths exactly like your offline script does
                wb = openpyxl.load_workbook(xlsx_path, data_only=True)
                tree = ET.parse(mxliff_path)
                root = tree.getroot()
                
                missing_items = []

                # =========================================================
                # ⬇️ PASTE YOUR EXACT CORE LOGIC HERE ⬇️
                # (Start from where you define your namespaces/dictionaries)
                # =========================================================
                
                
                
                # =========================================================
                # ⬆️ END OF YOUR CORE LOGIC ⬆️
                # =========================================================

                # --- Handle the CSV Output ---
                if not missing_items:
                    st.success("No hidden or missing strings found!")
                else:
                    csv_buffer = StringIO()
                    writer = csv.DictWriter(csv_buffer, fieldnames=['Cell', 'Source Text'])
                    writer.writeheader()
                    writer.writerows(missing_items)
                    
                    st.success(f"Report generated successfully! Found {len(missing_items)} hidden strings.")
                    
                    st.download_button(
                        label="Download CSV Report",
                        data=csv_buffer.getvalue(),
                        file_name="missing_strings_report.csv",
                        mime="text/csv"
                    )

            except Exception as e:
                st.error(f"An error occurred during processing:\n{e}")
                
            finally:
                # 3. Clean up the temporary files from the server
                if os.path.exists(xlsx_path):
                    os.remove(xlsx_path)
                if os.path.exists(mxliff_path):
                    os.remove(mxliff_path)
