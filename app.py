import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd
import gc
from utils.scraper import extract_items, clean_html
from utils.storage import load_previous_snapshot, save_snapshot, detect_new_items, push_bulk_snapshots
from utils.fetcher import fetch_html

# --- Load environment variables ---
load_dotenv()
PASSWORD = os.getenv("APP_PASSWORD") or st.secrets["APP_PASSWORD"]
CHUNK_SIZE = 10 # Num of rows processed before pushing to GitHub

# --- Page Config & Styling ---
st.set_page_config(
    page_title="LCN Consulting - Change Detection Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --primary-blue: #1e3a8a;
        --secondary-blue: #3b82f6;
        --success-green: #059669;
        --error-red: #dc2626;
        --new-yellow: #fcca05;
    }
    
    .lcn-header {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .company-name {
        font-family: 'Inter', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        color: white;
    }
    
    .tagline {
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        font-weight: 400;
        color: rgba(255, 255, 255, 0.9);
        margin-top: 0.5rem;
    }
    
    .status-success {
        background-color: #ecfdf5;
        border-left: 4px solid var(--success-green);
        padding: 0.75rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        color: #065f46;
    }
            
    .status-new {
        background-color: #fcf3cf;
        border-left: 4px solid var(--new-yellow);
        padding: 0.75rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        color: #5f5806;
    }
    
    .status-error {
        background-color: #fef2f2;
        border-left: 4px solid var(--error-red);
        padding: 0.75rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        color: #991b1b;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-blue), var(--secondary-blue));
        color: white;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
def create_header():
    st.markdown("""
    <div class="lcn-header">
        <h1 class="company-name">LCN Consulting</h1>
        <p class="tagline">Detecting Competitor Website Changes</p>
    </div>
    """, unsafe_allow_html=True)

# --- Sidebar ---
def create_sidebar():
    with st.sidebar:
        st.markdown("### 📋 Platform Overview")
        st.write("Monitor competitor websites for changes.")
        
        st.markdown("### 📊 Required Data Format")
        st.write("**Excel columns needed:**")
        st.write("• `Company`")
        st.write("• `URL`")
        st.write("• `URL Type`")

# --- Session State for Login ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- Login Page ---
if not st.session_state.authenticated:
    st.title("Login")
    password_input = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        if password_input == PASSWORD:
            st.session_state.authenticated = True
            st.success("Login successful!")
            st.rerun()  # Immediately refresh to show upload page
        else:
            st.error("Incorrect password")
    st.stop()

# --- Main Upload Page ---
create_header()
create_sidebar()
st.markdown("## 📂 Upload Configuration File")

uploaded_file = st.file_uploader(
    "Upload Competitor Configuration File",
    type=['xlsx', 'xls'],
    help="Upload Excel file containing competitor URLs"
)

if uploaded_file:
    st.write(f"Processing file: {uploaded_file.name}")

    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        st.stop()

    # Ensure required columns exist (case-insensitive)
    df.columns = df.columns.str.strip().str.lower()
    required_cols = ["url", "company", "url type"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Missing required column: {col}")
            st.stop()

    total_rows = len(df)
    progress_bar = st.progress(0)
    status_area = st.empty()
    results_log = []

    # --- Process in chunks ---
    for chunk_start in range(0, total_rows, CHUNK_SIZE):
        chunk_end = min(chunk_start + CHUNK_SIZE, total_rows)
        chunk = df.iloc[chunk_start:chunk_end]
    for index, row in chunk.iterrows():
        url = row["url"]
        company_name = row["company"]
        url_type = row["url type"]

        results_log.append(f"\nAccessing ({company_name}, {url_type}): {url}\n")

        try:
            html, source, status_code = fetch_html(url)
            cleaned_html = clean_html(html)

            if html:
                results_log.append(f"Success ({source}): {company_name}\n")

                items, error = extract_items(cleaned_html, url)
                if error:
                    results_log.append(f'<div class="status-error">🚨"⚠️ Could not extract structured content from {company_name} ({url_type}): {error}\n"</div>')
                    continue

                previous = load_previous_snapshot(company_name, url_type)
                new_items = detect_new_items(previous, items)

                if new_items:
                    results_log.append(f'<div class="status-new">🆕 {company_name} ({url_type}) - Changed</div>')
                    # for item in new_items:
                    #     results_log.append(f"    - {item['title']} ({item['timestamp']})\n")
                    #     results_log.append(f"      Link: {item['link']}\n")
                else:
                    results_log.append(f'<div class="status-success">✅ {company_name} ({url_type}) - No Change</div>')

                save_snapshot(company_name, url_type, items)
            else:
                if status_code == 404:
                    results_log.append(f'<div class="status-error">🚨 {company_name} ({url_type}) - Error {status_code}. Website does not exist. </div>')
                elif status_code == 403:
                    results_log.append(f'<div class="status-error">🚨 {company_name} ({url_type}) - Error {status_code}. Forbidden (bot detected).</div>')
                else:
                    results_log.append(f'<div class="status-error">🚨 {company_name} ({url_type}) - Error {status_code}. Failed to fetch, please check URL manually.</div>')

        except Exception as error:
            results_log.append(f'<div class="status-error">🚨 {company_name} ({url_type}) - Error {error}</div>')

        progress_bar.progress((index + 1) / total_rows)
        gc.collect()

    push_bulk_snapshots()
    st.markdown("## 📊 Change Detection Results")
    for entry in results_log:
        st.markdown(entry, unsafe_allow_html=True)

# --- Logout Button ---
if st.session_state.authenticated:
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
