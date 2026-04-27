import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup

# --- Page Config ---
st.set_page_config(page_title="LQA Dashboard", page_icon="🌍", layout="wide")

st.title("🌍 Localization Quality Manager Dashboard")
st.markdown("Upload your FanPolls CSV or MXLIFF files to review content and run automated QA checks.")

# --- File Uploader ---
uploaded_file = st.file_uploader("Upload a CSV or MXLIFF file", type=['csv', 'mxliff'])

if uploaded_file is not None:
    
    # ---------------------------------------------------------
    # CSV HANDLING LOGIC
    # ---------------------------------------------------------
    if uploaded_file.name.endswith('.csv'):
        st.subheader(f"Data Preview: {uploaded_file.name}")
        
        # Read the CSV
        df = pd.read_csv(uploaded_file)
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("🛠️ Quick QA Checks")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Run Character Limit Check"):
                # Example QA: Check if 'question_text' exceeds 100 characters
                if 'question_text' in df.columns:
                    df['Too Long'] = df['question_text'].str.len() > 100
                    issues = df[df['Too Long'] == True]
                    if not issues.empty:
                        st.warning(f"Found {len(issues)} questions over 100 characters!")
                        st.dataframe(issues[['artist_name', 'question_text', 'Too Long']])
                    else:
                        st.success("All questions pass the character limit check!")
                else:
                    st.error("Column 'question_text' not found in this CSV.")
                    
        with col2:
            if st.button("Check Missing Locales"):
                # Example QA: Check for empty locales
                if 'locale' in df.columns:
                    missing = df[df['locale'].isna()]
                    if not missing.empty:
                        st.warning(f"Found {len(missing)} rows with missing locales!")
                        st.dataframe(missing)
                    else:
                        st.success("No missing locales found!")
                else:
                    st.error("Column 'locale' not found in this CSV.")

    # ---------------------------------------------------------
    # MXLIFF HANDLING LOGIC
    # ---------------------------------------------------------
    elif uploaded_file.name.endswith('.mxliff'):
        st.subheader(f"Translation Preview: {uploaded_file.name}")
        
        # Parse the XML/MXLIFF file
        content = uploaded_file.getvalue().decode("utf-8")
        soup = BeautifulSoup(content, 'lxml-xml')
        
        # Extract translation units
        trans_units = soup.find_all('trans-unit')
        
        mxliff_data = []
        for tu in trans_units:
            source_text = tu.find('source').text if tu.find('source') else ""
            target_text = tu.find('target').text if tu.find('target') else ""
            status = tu.get('m:confirmed', '0') # Checks Memsource confirmation status
            
            mxliff_data.append({
                "Source (English)": source_text,
                "Target (Translation)": target_text,
                "Confirmed": "✅ Yes" if status == '1' else "⚠️ No"
            })
            
        mxliff_df = pd.DataFrame(mxliff_data)
        st.dataframe(mxliff_df, use_container_width=True)
        
        st.divider()
        st.subheader("🛠️ MXLIFF QA Checks")
        
        if st.button("Find Missing Translations"):
            # Check for empty target segments
            missing_translations = mxliff_df[mxliff_df["Target (Translation)"] == ""]
            if not missing_translations.empty:
                st.error(f"Found {len(missing_translations)} missing translations!")
                st.dataframe(missing_translations)
            else:
                st.success("All segments have target text!")
