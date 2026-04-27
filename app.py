import streamlit as st
import openpyxl
import xml.etree.ElementTree as ET
import csv
import re
from io import StringIO, BytesIO  # <-- Added BytesIO here

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
            try:
                # THE FIX: Read Streamlit's stream into a standard Python byte buffer
                xlsx_buffer = BytesIO(xlsx_file.read())
                mxliff_buffer = BytesIO(mxliff_file.read())

                # Load the files from the pure byte buffers
                wb = openpyxl.load_workbook(xlsx_buffer, data_only=True)
                tree = ET.parse(mxliff_buffer)
                root = tree.getroot()
                
                missing_items = []

                # =========================================================
                # ⬇️ PASTE YOUR EXACT CORE LOGIC HERE ⬇️
                # (No changes needed to your original regex or matching loops)
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
