"""
ScrAPEM - Intelligent Datasheet Extractor
Hybrid AI + Deterministic Python Extraction Pipeline (v4.2)
"""

import streamlit as st
import pandas as pd
import io
import zipfile
from datetime import datetime

# Import modules
from extract_ai import render_pdf_to_images, extract_with_ai, normalize_ai_output
from extract_python import extract_from_buffer, get_low_confidence_fields, get_confidence_icon, PRODUCT_TYPES
from merge_results import merge_product_data, format_for_output

# --- CONFIGURATION ---
# API keys should be entered via UI or stored in Streamlit secrets
DEFAULT_GOOGLE_KEY = ""
DEFAULT_OPENAI_KEY = ""

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Extractor | ScrAPEM", 
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
    
    /* Hide dotted border around file uploader pagination */
    .stFileUploader [data-testid="stFileUploaderPagination"] {
        border: none !important;
    }
    
    .stFileUploader small {
        border: none !important;
    }
    
    [data-testid="stFileUploaderDropzoneInstructions"] + div {
        border: none !important;
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
    
    /* Download buttons - green gradient */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
        color: white !important;
        font-weight: 600;
        border: none;
        border-radius: 10px;
    }
    
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #047857 0%, #059669 100%) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("assets/apem_logo.png", width=150)
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
    <h1>📄 ScrAPEM v5.3</h1>
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
    est_cost = est_pages * 0.003  # $0.003 per page for GPT-4o-mini vision (only for low-conf fields)
    
    # Time estimate: Python is fast (~0.5s per page), AI adds ~1s per page if enabled
    python_time = est_pages * 0.5  # Python extraction: ~0.5 seconds per page
    ai_time = est_pages * 1.0 if use_hybrid else 0  # AI enhancement adds ~1s per page
    est_time = python_time + ai_time + (len(uploaded_files) * 0.5)  # Add overhead per file
    
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
    mins, secs = divmod(int(est_time), 60)
    if mins > 0:
        time_str = f"{mins}m {secs}s"
    else:
        time_str = f"{secs}s"
    st.info(f"⏱️ Estimated processing time: **{time_str}**")
    
    st.markdown("")
    
    if st.button("🚀 Start Extraction", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_files = {} 
        results_metadata = {}  # Store confidence info per file
        
        for i, uploaded_file in enumerate(uploaded_files):
            progress = (i + 1) / len(uploaded_files)
            progress_bar.progress(progress)
            status_text.text(f"⏳ Processing {uploaded_file.name}...")
            
            # Step 1: Python Extraction (with confidence tracking)
            uploaded_file.seek(0)
            python_result = extract_from_buffer(uploaded_file, uploaded_file.name)
            
            product_type = python_result.get('_PRODUCT_TYPE', 'LED Indicator')
            confidence_score = python_result.get('_confidence_score', 0)
            confidence_level = python_result.get('_confidence_level', 'low')
            validation = python_result.get('_validation', {})
            
            # Get low confidence fields for AI enhancement
            low_conf_fields = get_low_confidence_fields(python_result)
            
            # Step 2: AI Enhancement (only for low confidence fields if enabled)
            if use_hybrid and api_key and low_conf_fields:
                status_text.text(f"⏳ AI enhancing {len(low_conf_fields)} fields in {uploaded_file.name}...")
                
                uploaded_file.seek(0)
                pdf_bytes = uploaded_file.read()
                images = render_pdf_to_images(pdf_bytes, max_pages=5, scale=3)  # Smaller for faster AI
                
                ai_raw = extract_with_ai(images, api_key, provider=provider)
                ai_products = normalize_ai_output(ai_raw)
                
                # Merge: Python as base, AI fills gaps
                if ai_products:
                    ai_data = ai_products[0] if ai_products else {}
                    for field_info in low_conf_fields:
                        field = field_info['field']
                        ai_value = ai_data.get(field)
                        if ai_value and ai_value not in [None, "", "null", "N/A"]:
                            python_result[field] = ai_value
                            # Update validation
                            if field in validation:
                                validation[field]['confidence'] = 'medium'
                                validation[field]['icon'] = '🟡'
                                validation[field]['source'] = 'AI Enhanced'
            
            # Build output row (exclude internal fields)
            output_row = {k: v for k, v in python_result.items() if not k.startswith('_')}
            
            # Store metadata for display
            results_metadata[uploaded_file.name] = {
                'product_type': product_type,
                'confidence_score': confidence_score,
                'confidence_level': confidence_level,
                'validation': validation,
                'low_conf_count': len(low_conf_fields)
            }
            
            # Create DataFrame
            df = pd.DataFrame([output_row])
            processed_files[uploaded_file.name] = df
        # Build product type summary
        product_type_counts = {}
        for fname, meta in results_metadata.items():
            ptype = meta.get('product_type', 'Unknown')
            product_type_counts[ptype] = product_type_counts.get(ptype, 0) + 1
        
        type_summary = ", ".join([f"{count} {ptype}" for ptype, count in product_type_counts.items()])
        
        # Success message
        st.markdown(f"""
        <div class="success-box">
            <h3 style="color: white; margin: 0;">✅ Extraction Complete! 🚀</h3>
            <p style="color: white; margin: 0.5rem 0 0 0;">Successfully extracted data from {len(processed_files)} file(s)</p>
            <p style="color: rgba(255,255,255,0.9); margin: 0.25rem 0 0 0; font-style: italic;">Product types: {type_summary}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if processed_files:
            st.markdown("### 📋 Extracted Data")
            
            # Legend box
            st.markdown("""
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem;">
                <strong>📖 Legend:</strong><br>
                <span style="background-color: #fee2e2; color: #dc2626; padding: 2px 6px; border-radius: 4px; font-weight: bold;">N/A</span>
                = Value expected but not found in the PDF (missing data)<br>
                <span style="color: #6b7280;">—</span> = Field not applicable for this product type<br><br>
                <strong>🔍 Confidence Levels:</strong><br>
                🟢 <strong>High</strong> = Multiple options found with proper Code:Value format<br>
                🟡 <strong>Medium</strong> = Value found but single option or incomplete format<br>
                🔴 <strong>Low</strong> = Value not found or uncertain extraction
            </div>
            """, unsafe_allow_html=True)
            
            # Helper function to highlight N/A cells
            def highlight_na(val):
                if val == 'N/A':
                    return 'background-color: #fee2e2; color: #dc2626; font-weight: bold;'
                return ''
            
            # Show confidence summary per file
            for fname, df in processed_files.items():
                meta = results_metadata.get(fname, {})
                conf_icon = get_confidence_icon(meta.get('confidence_level', 'low'))
                product_type = meta.get('product_type', 'Unknown')
                conf_score = meta.get('confidence_score', 0)
                low_conf = meta.get('low_conf_count', 0)
                
                with st.expander(f"📄 **{fname}** | {conf_icon} {conf_score}% confidence | Type: {product_type}", expanded=True):
                    # Metrics row
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Product Type", product_type)
                    m2.metric("Confidence", f"{conf_score}%")
                    m3.metric("Fields Found", len([c for c in df.columns if df[c].iloc[0] != 'N/A']))
                    m4.metric("AI Enhanced", low_conf if use_hybrid else 0)
                    
                    # Data table with N/A highlighting
                    styled_df = df.style.applymap(highlight_na)
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Validation details
                    validation = meta.get('validation', {})
                    if validation:
                        with st.expander("🔍 Field Validation Details", expanded=False):
                            for field, info in sorted(validation.items()):
                                icon = info.get('icon', '⚪')
                                source = info.get('source', 'Unknown')
                                reason = info.get('reason', '')
                                page = info.get('page')
                                
                                # Format source with page if available
                                if page and source and source != 'None':
                                    source_str = f"{source} - Page {page}"
                                elif page:
                                    source_str = f"Page {page}"
                                else:
                                    source_str = source if source else 'Unknown'
                                
                                st.markdown(f"{icon} **{field}**: {reason} | Source: {source_str}")
            
            # Download button - All files
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
            
            # Individual file downloads
            if len(processed_files) > 1:
                st.markdown("---")
                st.markdown("##### 📄 Download Individual Files (by Series)")
                
                # Create columns for buttons (3 per row)
                file_list = list(processed_files.items())
                cols_per_row = 3
                
                for i in range(0, len(file_list), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        idx = i + j
                        if idx < len(file_list):
                            fname, df = file_list[idx]
                            # Get series name from the data
                            series_name = df['SERIES'].iloc[0] if 'SERIES' in df.columns else fname.replace('.pdf', '')
                            
                            # Create individual Excel file
                            individual_buffer = io.BytesIO()
                            with pd.ExcelWriter(individual_buffer, engine='openpyxl') as writer:
                                df.to_excel(writer, index=False)
                            
                            with col:
                                st.download_button(
                                    label=f"📄 {series_name}",
                                    data=individual_buffer.getvalue(),
                                    file_name=f"{series_name}_Output.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True,
                                    key=f"download_{idx}"
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
