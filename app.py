"""
ScrAPEM - Intelligent Datasheet Extractor
Hybrid AI + Deterministic Python Extraction Pipeline
"""

import streamlit as st
import pandas as pd
import io
import zipfile
from datetime import datetime

# Import modules
from extract_ai import render_pdf_to_images, extract_with_ai, normalize_ai_output
from extract_data_deterministic import extract_from_buffer
from merge_results import merge_product_data, format_for_output

# --- CONFIGURATION ---
# API keys should be entered via UI or stored in Streamlit secrets
DEFAULT_GOOGLE_KEY = ""
DEFAULT_OPENAI_KEY = ""

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="ScrAPEM - Datasheet Extractor", 
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Main styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Stats cards */
    .stat-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        border-left: 4px solid #667eea;
    }
    
    .stat-card h3 {
        margin: 0;
        color: #667eea;
        font-size: 1.8rem;
    }
    
    .stat-card p {
        margin: 0.25rem 0 0 0;
        color: #666;
        font-size: 0.9rem;
    }
    
    /* Success message */
    .success-box {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    /* File upload area styling */
    .stFileUploader > div > div {
        border: 2px dashed #667eea !important;
        border-radius: 10px !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/document.png", width=60)
    st.markdown("### ⚙️ Configuration")
    st.markdown("---")
    
    use_hybrid = st.checkbox("🔄 Use Hybrid AI + Python", value=True, 
                             help="Combines AI vision with deterministic Python extraction")
    
    st.markdown("#### AI Provider")
    ai_provider = st.selectbox("", ["OpenAI (GPT-4o-mini)", "Google (Gemini)"], 
                               index=0, label_visibility="collapsed")
    
    if ai_provider.startswith("OpenAI"):
        api_key = st.text_input("🔑 API Key", value=DEFAULT_OPENAI_KEY, type="password")
        provider = "openai"
    else:
        api_key = st.text_input("🔑 API Key", value=DEFAULT_GOOGLE_KEY, type="password")
        provider = "google"
    
    st.markdown("---")
    st.markdown("#### 📊 About")
    st.markdown("""
    **ScrAPEM** extracts product specifications from PDF datasheets using:
    - 🤖 **AI Vision** - GPT-4o-mini
    - 🐍 **Python Regex** - Deterministic
    - 🔀 **Smart Merge** - Best of both
    """)

# --- MAIN CONTENT ---
st.markdown("""
<div class="main-header">
    <h1>📄 ScrAPEM v4.2</h1>
    <p>Intelligent Datasheet Extractor — Upload PDFs and extract product specifications automatically</p>
</div>
""", unsafe_allow_html=True)

# File upload
uploaded_files = st.file_uploader(
    "📁 Drop PDF datasheets here",
    type="pdf",
    accept_multiple_files=True,
    help="Upload one or more PDF product datasheets"
)

if uploaded_files:
    # Estimate pages (rough: 100KB per page)
    est_pages = sum(max(1, int(f.size / 102400)) for f in uploaded_files)
    est_cost = est_pages * 0.003  # $0.003 per page for GPT-4o-mini vision
    est_time = est_pages * 3  # ~3 seconds per page
    
    # Show stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <h3>{len(uploaded_files)}</h3>
            <p>Files uploaded</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        total_size = sum(f.size for f in uploaded_files) / (1024 * 1024)
        st.markdown(f"""
        <div class="stat-card">
            <h3>{total_size:.1f} MB</h3>
            <p>Total size</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <h3>~{est_pages}</h3>
            <p>Est. pages</p>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="stat-card" style="border-left-color: #38ef7d;">
            <h3>${est_cost:.3f}</h3>
            <p>Est. API cost</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Show ETA
    if use_hybrid:
        mins, secs = divmod(est_time, 60)
        st.info(f"⏱️ Estimated processing time: **{int(mins)}m {int(secs)}s** (AI extraction)")
    
    st.markdown("")
    
    if st.button("🚀 Start Extraction", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_files = {} 
        target_columns = ['SERIES', 'MODEL_CODE', 'MOUNTING HOLE', 'BEZEL STYLE', 'TERMINALS', 
                          'BEZEL FINISH', 'TYPE OF ILLUMINATION', 'LED COLOR', 'VOLTAGE', 'SEALING']
        
        for i, uploaded_file in enumerate(uploaded_files):
            progress = (i + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(f"⏳ Processing {uploaded_file.name}...")
            
            file_results = []
            
            if use_hybrid and api_key:
                # Step 1: Python Extraction
                uploaded_file.seek(0)
                python_result = extract_from_buffer(uploaded_file, uploaded_file.name)
                python_specs = python_result.get('specs', {})
                python_model_codes = python_result.get('model_codes', [])
                
                # Step 2: AI Extraction
                uploaded_file.seek(0)
                pdf_bytes = uploaded_file.read()
                images = render_pdf_to_images(pdf_bytes, max_pages=10, scale=4)
                
                ai_raw = extract_with_ai(images, api_key, provider=provider)
                ai_products = normalize_ai_output(ai_raw)
                
                # Step 3: Merge
                merged = merge_product_data(ai_products, python_result)
                file_results = format_for_output(merged)
                
                # Debug expander
                with st.expander(f"🔍 Debug: {uploaded_file.name}", expanded=False):
                    dcol1, dcol2 = st.columns(2)
                    with dcol1:
                        st.metric("AI Products", len(ai_products))
                        st.metric("Pages Processed", len(images))
                    with dcol2:
                        st.metric("Final Products", len(file_results))
                        st.metric("Python Specs", len(python_specs))
                    
                    st.markdown("**AI Raw Output (first 3):**")
                    st.json(ai_raw[:3] if len(ai_raw) > 3 else ai_raw)
                    
            else:
                # Python-only fallback
                uploaded_file.seek(0)
                python_result = extract_from_buffer(uploaded_file, uploaded_file.name)
                merged = merge_product_data([], python_result)
                file_results = format_for_output(merged)
            
            if file_results:
                df = pd.DataFrame(file_results)
                df = df.reindex(columns=target_columns)
                processed_files[uploaded_file.name] = df
        
        # Success message
        st.markdown("""
        <div class="success-box">
            ✅ <strong>Extraction Complete!</strong> Found products in all uploaded files.
        </div>
        """, unsafe_allow_html=True)
        
        if processed_files:
            st.markdown("### 📊 Results Preview")
            
            # Tabs for each file
            if len(processed_files) > 1:
                tabs = st.tabs(list(processed_files.keys()))
                for tab, (fname, df) in zip(tabs, processed_files.items()):
                    with tab:
                        st.dataframe(df, use_container_width=True)
            else:
                first_name = list(processed_files.keys())[0]
                st.dataframe(processed_files[first_name], use_container_width=True)
            
            # Download button
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for fname, df in processed_files.items():
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    excel_data = excel_buffer.getvalue()
                    xlsx_name = fname.replace('.pdf', '.xlsx')
                    zf.writestr(xlsx_name, excel_data)
            
            st.markdown("")
            st.download_button(
                label="📥 Download All Results (ZIP)",
                data=zip_buffer.getvalue(),
                file_name=f"ScrAPEM_Export_{datetime.now().strftime('%Y%m%d_%H%M')}.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.warning("⚠️ No data extracted from the uploaded files.")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.85rem;">
    © 2025 ScrAPEM Intelligence. All rights reserved.
</div>
""", unsafe_allow_html=True)
