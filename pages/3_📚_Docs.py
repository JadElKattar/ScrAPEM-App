"""
ScrAPEM - Documentation Page
"""
import streamlit as st
from components.navbar import render_navbar

st.set_page_config(
    page_title="Docs | ScrAPEM",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
    }
    
    .docs-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
    }
    
    .step-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    
    .code-block {
        background: #1e1e1e;
        color: #d4d4d4;
        padding: 1rem;
        border-radius: 8px;
        font-family: monospace;
    }
    
    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    [data-testid="stSidebarCollapsedControl"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# Render header navbar
render_navbar(current_page="Docs")

# Docs Header
st.markdown("""
<div class="docs-header">
    <h1>📚 Documentation</h1>
    <p>Learn how to use ScrAPEM effectively</p>
</div>
""", unsafe_allow_html=True)

# Quick Start
st.markdown("## 🚀 Quick Start")
st.markdown("""
<div class="step-card">
    <h4>Step 1: Upload PDFs</h4>
    <p>Drag and drop your APEM product datasheet PDFs into the upload area. 
    You can upload multiple files at once.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="step-card">
    <h4>Step 2: Configure (Optional)</h4>
    <p>Enable <strong>Hybrid AI + Python</strong> mode for enhanced extraction. 
    Enter your OpenAI API key if you want AI enhancement for low-confidence fields.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="step-card">
    <h4>Step 3: Extract</h4>
    <p>Click <strong>Start Extraction</strong> and wait for processing. 
    You'll see real-time progress and confidence scores.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="step-card">
    <h4>Step 4: Download</h4>
    <p>Download all results as a ZIP file, or download individual files by series name.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Supported Product Types
st.markdown("## 📋 Supported Product Types")

col1, col2 = st.columns(2)
with col1:
    st.markdown("### LED Indicators")
    st.markdown("""
    - HS1T Series
    - NRA Series
    - APSeries
    - FT2J Series
    
    **Extracted Fields:**
    - Series, Mounting Hole, Bezel Style
    - Terminals, Bezel Finish
    - LED Color, Voltage, Sealing
    """)
    
    st.markdown("### Terminal Blocks")
    st.markdown("""
    - BN-W Series
    - BNH-W Series
    
    **Extracted Fields:**
    - Series, Wire Size, Connection Type
    - Voltage Rating, Current Rating
    """)

with col2:
    st.markdown("### Joysticks")
    st.markdown("""
    - BHN (Paddle Joystick)
    - CJ (Thumbstick/Hand Grip)
    - XF/XS (Fingertip Joystick)
    
    **Extracted Fields:**
    - Series, Configuration, Axis
    - Output, Voltage, Mounting
    - Button Options, Spring Tension
    """)

st.markdown("---")

# Output Format
st.markdown("## 📊 Output Format")
st.markdown("""
All multi-option fields are formatted as:
""")
st.code("{Code:Value|Code:Value}", language="text")
st.markdown("""
**Example:**
""")
st.code("{R:Red|G:Green|B:Blue|W:White}", language="text")

st.markdown("---")

# Confidence Levels
st.markdown("## 🔍 Confidence Levels")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("### 🟢 High")
    st.markdown("Multiple options found with proper Code:Value format. Extracted from tables or ordering information.")
with col2:
    st.markdown("### 🟡 Medium")
    st.markdown("Value found but single option or incomplete format. May need review.")
with col3:
    st.markdown("### 🔴 Low")
    st.markdown("Value not found or uncertain extraction. AI enhancement attempted if enabled.")

st.markdown("---")

# API Key Setup
st.markdown("## 🔑 API Key Setup")
st.markdown("""
To enable AI enhancement for low-confidence fields:

1. Get an API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Enter it in the sidebar under **API Key**
3. Enable **Use Hybrid AI + Python** mode

**Note:** API keys are not stored. You'll need to enter them each session.
""")

st.markdown("---")

# Footer
st.markdown("""
<div style="text-align: center; color: #888;">
    © 2025 ScrAPEM Intelligence | Built by Jad El Kattar, Alessandro Vigano, Nikita Marushko | Powered by APEM
</div>
""", unsafe_allow_html=True)
