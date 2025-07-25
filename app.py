import streamlit as st
import pandas as pd
import os
from datetime import datetime
import base64
from io import BytesIO
import subprocess
import sys
import tempfile

try:
    from utils.storage import load_previous_snapshot, save_snapshot, detect_new_items
    from curl_cffi import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    import re
except ImportError as e:
    st.error(f"Required modules not found: {e}")
    st.stop()

def extract_items(html_content, base_url):
    junk_keywords = ["skip", "main menu", "footer", "cookie"]
    soup = BeautifulSoup(html_content, 'html.parser')
    items = []

    candidates = soup.find_all(['article', 'li', 'tr', 'div', 'section', 'p'])

    for tag in candidates:
        text = tag.get_text(strip=True)
        if not text or any(j in text.lower() for j in junk_keywords):
            continue

        link_tag = tag.find('a')
        date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', text)

        if link_tag and text:
            raw_link = link_tag.get('href')
            full_link = urljoin(base_url, raw_link) if raw_link else base_url

            items.append({
                "title": text[:150],
                "link": full_link,
                "timestamp": date_match.group(0) if date_match else "unknown"
            })

    if not items:
        return [], "No extractable content found (possibly dynamic site or unsupported structure)"

    return items, None

st.set_page_config(
    page_title="LCN Consulting - Competitive Intelligence Platform",
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
        --accent-blue: #60a5fa;
        --light-blue: #f0f9ff;
        --dark-text: #1f2937;
        --medium-gray: #6b7280;
        --light-gray: #f8fafc;
        --success-green: #059669;
        --warning-orange: #d97706;
        --error-red: #dc2626;
    }
    
    .main > div {
        padding-top: 2rem;
    }
    
    .lcn-header {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--secondary-blue) 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(30, 58, 138, 0.2);
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
        line-height: 1.4;
    }
    
    .status-success {
        background-color: #ecfdf5;
        border-left: 4px solid var(--success-green);
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        color: #065f46;
    }
    
    .status-warning {
        background-color: #fffbeb;
        border-left: 4px solid var(--warning-orange);
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        color: #92400e;
    }
    
    .status-error {
        background-color: #fef2f2;
        border-left: 4px solid var(--error-red);
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        color: #991b1b;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-blue), var(--secondary-blue));
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(30, 58, 138, 0.3);
    }
    
    .stProgress > div > div > div {
        background: linear-gradient(135deg, var(--primary-blue), var(--secondary-blue));
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def create_professional_header():
    st.markdown("""
    <div class="lcn-header">
        <h1 class="company-name">LCN consulting</h1>
        <p class="tagline">Maximize Your Brand Advantage Through Competitive Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

def create_sidebar():
    with st.sidebar:
        st.markdown("### 📋 Platform Overview")
        st.write("Monitor competitor websites and deliver actionable insights to maximize your brand advantage.")
        
        st.markdown("### 📊 Required Data Format")
        st.write("**Excel columns needed:**")
        st.write("• `Company` - Competitor name")
        st.write("• `URL` - Website to monitor")
        st.write("• `URL Type` - Content category")

def process_monitoring_file(file_path, monitoring_params):
    try:
        df = pd.read_excel(file_path)
        
        if 'URL' not in df.columns:
            raise ValueError("Expected a column named URL in the sheet.")
        
        results = []
        csv_data = []
        
        for index, row in df.iterrows():
            url = row['URL']
            company_name = row['Company']
            url_type = row['URL Type']
            
            result_msg = f"Accessing ({company_name}, {url_type}): {url}"
            results.append(result_msg)
            
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                
                response = requests.get(
                    url, 
                    timeout=monitoring_params.get('timeout_duration', 30), 
                    impersonate="chrome110",
                    headers=headers,
                )
                
                if response.status_code == 200:
                    results.append(f"Success: {company_name}")
                    
                    html = response.text
                    items, error = extract_items(html, url)
                    
                    if error:
                        results.append(f"  ⚠️ Could not extract structured content: {error}")
                        csv_data.append({
                            'Company': company_name,
                            'URL': url,
                            'URL_Type': url_type,
                            'Status': 'Error',
                            'Message': error,
                            'Items_Found': 0,
                            'New_Items': 0,
                            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        continue
                    
                    previous = load_previous_snapshot(company_name, url_type)
                    new_items = detect_new_items(previous, items)
                    
                    if new_items:
                        results.append(f"  🆕 {len(new_items)} new item(s) found:")
                        for item in new_items:
                            results.append(f"    - {item['title']} ({item['timestamp']})")
                            results.append(f"      Link: {item['link']}")
                            
                            csv_data.append({
                                'Company': company_name,
                                'URL': url,
                                'URL_Type': url_type,
                                'Status': 'Success',
                                'Title': item['title'],
                                'Link': item['link'],
                                'Timestamp': item['timestamp'],
                                'Is_New': True,
                                'Scan_Time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                    else:
                        results.append("  ✅ No new content since last check.")
                        csv_data.append({
                            'Company': company_name,
                            'URL': url,
                            'URL_Type': url_type,
                            'Status': 'Success',
                            'Message': 'No new content',
                            'Items_Found': len(items),
                            'New_Items': 0,
                            'Is_New': False,
                            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    
                    save_snapshot(company_name, url_type, items)
                    
                elif response.status_code == 404:
                    msg = f" 🚨 Failure: Status code {response.status_code}. Website does not exist."
                    results.append(msg)
                    csv_data.append({
                        'Company': company_name,
                        'URL': url,
                        'URL_Type': url_type,
                        'Status': 'Error',
                        'Message': '404 - Website does not exist',
                        'Status_Code': response.status_code,
                        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                elif response.status_code == 403:
                    msg = f" 🚨 Failure: Status code {response.status_code}. Likely detected as a bot."
                    results.append(msg)
                    csv_data.append({
                        'Company': company_name,
                        'URL': url,
                        'URL_Type': url_type,
                        'Status': 'Error',
                        'Message': '403 - Detected as bot',
                        'Status_Code': response.status_code,
                        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                else:
                    msg = f" 🚨 Failure: Status code {response.status_code}. Please check manually."
                    results.append(msg)
                    csv_data.append({
                        'Company': company_name,
                        'URL': url,
                        'URL_Type': url_type,
                        'Status': 'Error',
                        'Message': f'HTTP {response.status_code}',
                        'Status_Code': response.status_code,
                        'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
            except Exception as error:
                error_msg = f" 🚨 Failed to fetch {url}: {error}"
                results.append(error_msg)
                csv_data.append({
                    'Company': company_name,
                    'URL': url,
                    'URL_Type': url_type,
                    'Status': 'Error',
                    'Message': str(error),
                    'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        
        return results, csv_data
        
    except Exception as e:
        return [f"Error processing file: {str(e)}"], []

def main():
    create_professional_header()
    create_sidebar()
    st.markdown("## 🎯 Competitive Intelligence Configuration")
    
    uploaded_file = st.file_uploader(
        "Upload Competitor Configuration File",
        type=['xlsx', 'xls'],
        help="Upload Excel file containing competitor URLs to monitor"
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            required_columns = ['URL', 'Company', 'URL Type']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.markdown(f"""
                <div class="status-error">
                    <strong>❌ Configuration Error</strong><br>
                    Missing required columns: {', '.join(missing_columns)}<br>
                    Expected columns: {', '.join(required_columns)}
                </div>
                """, unsafe_allow_html=True)
                return
            
            st.markdown(f"""
            <div class="status-success">
                <strong>✅ Configuration Loaded Successfully</strong><br>
                Ready to monitor {len(df)} competitor URLs across {df['Company'].nunique()} companies
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("📊 Preview Configuration Data", expanded=False):
                st.dataframe(df, use_container_width=True, height=300)
            
            st.markdown("### ⚙️ Intelligence Parameters")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                scan_frequency = st.selectbox(
                    "Scan Frequency",
                    ["Real-time", "Hourly", "Daily", "Weekly"],
                    index=0
                )
            
            with col2:
                content_depth = st.selectbox(
                    "Content Analysis Depth",
                    ["Surface", "Standard", "Deep", "Comprehensive"],
                    index=1
                )
            
            with col3:
                report_format = st.selectbox(
                    "Report Format",
                    ["CSV", "Excel", "JSON", "PDF"],
                    index=0
                )
            
            with st.expander("🔧 Advanced Configuration", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    include_images = st.checkbox("Include Image Analysis", value=False)
                    track_sentiment = st.checkbox("Sentiment Analysis", value=False)
                    detect_keywords = st.checkbox("Keyword Detection", value=True)
                
                with col2:
                    timeout_duration = st.slider("Request Timeout (seconds)", 10, 60, 30)
                    retry_attempts = st.slider("Retry Attempts", 1, 5, 3)
                
                custom_keywords = st.text_area(
                    "Custom Keywords (comma-separated)",
                    placeholder="innovation, product launch, partnership, acquisition"
                )
            
            st.markdown("### 🚀 Execute Intelligence Gathering")
            
            monitoring_params = {
                'scan_frequency': scan_frequency,
                'content_depth': content_depth,
                'report_format': report_format,
                'include_images': include_images,
                'track_sentiment': track_sentiment,
                'detect_keywords': detect_keywords,
                'timeout_duration': timeout_duration,
                'retry_attempts': retry_attempts,
                'custom_keywords': custom_keywords.split(',') if custom_keywords else []
            }
            
            if st.button("🎯 Launch Intelligence Analysis", type="primary", use_container_width=True):
                with st.spinner("🔍 Executing competitive intelligence analysis..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    results, csv_data = process_monitoring_file(tmp_file_path, monitoring_params)
                    
                    os.unlink(tmp_file_path)
                    
                    progress_bar.progress(100)
                    status_text.success("✅ Intelligence analysis complete!")
                
                if results and csv_data:
                    st.markdown("## 📊 Intelligence Analysis Results")
                    
                    csv_df = pd.DataFrame(csv_data)
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Intelligence Items", len(csv_df))
                    with col2:
                        new_items = len(csv_df[csv_df.get('Is_New', False) == True]) if 'Is_New' in csv_df.columns else 0
                        st.metric("New Intelligence", new_items, delta=f"+{new_items}")
                    with col3:
                        successful_scans = len(csv_df[csv_df.get('Status', '') == 'Success']) if 'Status' in csv_df.columns else 0
                        st.metric("Successful Scans", successful_scans)
                    with col4:
                        companies_monitored = csv_df['Company'].nunique() if 'Company' in csv_df.columns else 0
                        st.metric("Companies Analyzed", companies_monitored)
                    
                    with st.expander("📋 Detailed Intelligence Log", expanded=True):
                        for result in results:
                            if "🆕" in result or "new" in result.lower():
                                st.markdown(f'<div class="status-success">{result}</div>', unsafe_allow_html=True)
                            elif "⚠️" in result or "warning" in result.lower():
                                st.markdown(f'<div class="status-warning">{result}</div>', unsafe_allow_html=True)
                            elif "🚨" in result or "error" in result.lower():
                                st.markdown(f'<div class="status-error">{result}</div>', unsafe_allow_html=True)
                            else:
                                st.info(result)
                    
                    if csv_data:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"LCN_Intelligence_Report_{timestamp}.csv"
                        
                        csv = csv_df.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Intelligence Report",
                            data=csv,
                            file_name=filename,
                            mime="text/csv",
                            type="primary",
                            use_container_width=True
                        )
                        
                        with st.expander("📋 Report Data Preview", expanded=False):
                            st.dataframe(csv_df, use_container_width=True)
        
        except Exception as e:
            st.markdown(f"""
            <div class="status-error">
                <strong>❌ File Processing Error</strong><br>
                {str(e)}<br>
                Please verify your Excel file format and try again.
            </div>
            """, unsafe_allow_html=True)
            
            st.write("Debug info:")
            st.write(f"Error type: {type(e).__name__}")
            st.write(f"Error details: {str(e)}")
            
            import traceback
            st.code(traceback.format_exc())

if __name__ == "__main__":
    main()