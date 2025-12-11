"""
ScrAPEM - Home Page (Landing)
Intelligent Datasheet Extractor by APEM
"""
import streamlit as st
from components.navbar import render_navbar

st.set_page_config(
    page_title="ScrAPEM - APEM Datasheet Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
    }
    
    .hero-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem;
        border-radius: 16px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .hero-section h1 {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    .hero-section p {
        font-size: 1.2rem;
        opacity: 0.9;
    }
    
    .feature-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        height: 100%;
        min-height: 220px;
        border: 1px solid #e2e8f0;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    .stat-item {
        text-align: center;
    }
    
    .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        color: #667eea;
    }
    
    .stat-label {
        color: #666;
        font-size: 0.9rem;
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
render_navbar(current_page="Home")

# Hero Section
st.markdown("""
<div class="hero-section">
    <h1>📄 ScrAPEM v5.5</h1>
    <p>AI-Powered Datasheet Extraction for APEM Products</p>
    <p style="font-size: 1rem; opacity: 0.8; margin-top: 1rem;">
        Extract technical specifications from PDF datasheets in seconds
    </p>
</div>
""", unsafe_allow_html=True)

# Feature Cards
st.markdown("## ✨ Key Features")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🐍</div>
        <h4>Python-First</h4>
        <p>Deterministic regex-based extraction for reliable, consistent results</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🤖</div>
        <h4>AI Enhanced</h4>
        <p>GPT-4o-mini fills gaps in low-confidence fields automatically</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">📊</div>
        <h4>Multi-Product</h4>
        <p>Auto-detects LEDs, joysticks, terminal blocks & other product types</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🔍</div>
        <h4>Confidence Tracking</h4>
        <p>See extraction quality with 🟢🟡🔴 indicators per field</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")

st.markdown("---")

# Stats Section
st.markdown("## 📈 Extraction Capabilities")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("""
    <div class="stat-item">
        <div class="stat-number">5+</div>
        <div class="stat-label">Product Types Supported</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div class="stat-item">
        <div class="stat-number">15+</div>
        <div class="stat-label">Fields Extracted</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div class="stat-item">
        <div class="stat-number">~0.5s</div>
        <div class="stat-label">Per Page (Python)</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown("""
    <div class="stat-item">
        <div class="stat-number">95%+</div>
        <div class="stat-label">Extraction Accuracy</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# How It Works
st.markdown("## 🔄 How It Works")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 1️⃣ Upload")
    st.markdown("Drop your APEM PDF datasheets")
with col2:
    st.markdown("### 2️⃣ Extract")
    st.markdown("Python parses tables & text")
with col3:
    st.markdown("### 3️⃣ Enhance")
    st.markdown("AI fills low-confidence gaps")
with col4:
    st.markdown("### 4️⃣ Download")
    st.markdown("Get Excel files per series")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.85rem;">
    © 2025 ScrAPEM Intelligence | Built by Jad El Kattar, Alessandro Vigano, Nikita Marushko | Powered by APEM
</div>
""", unsafe_allow_html=True)
