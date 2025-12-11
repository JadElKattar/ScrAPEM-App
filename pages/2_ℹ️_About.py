"""
ScrAPEM - About Page
"""
import streamlit as st
from components.navbar import render_navbar

st.set_page_config(
    page_title="About | ScrAPEM",
    page_icon="ℹ️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
    }
    
    .about-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
    }
    
    .about-header h1 {
        margin: 0;
        font-size: 2rem;
    }
    
    .about-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    
    .team-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
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
render_navbar(current_page="About")

# About Header
st.markdown("""
<div class="about-header">
    <h1>ℹ️ About ScrAPEM</h1>
    <p>AI-Powered Datasheet Extraction for APEM Product Documentation</p>
</div>
""", unsafe_allow_html=True)

# About Section
st.markdown("## 🏢 About APEM")
st.markdown("""
<div class="about-card">
    <p><strong>APEM</strong> is part of the <strong>IDEC Corporation</strong> group, a world-leading manufacturer of 
    human-machine interface components including switches, joysticks, indicators, and control panels.</p>
    <p>With over 70 years of expertise, APEM designs and manufactures high-quality components used in 
    industrial, medical, aerospace, and transportation applications worldwide.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("## 🎯 About This Project")
st.markdown("""
<div class="about-card">
    <p><strong>ScrAPEM</strong> (Smart-Capture-Really-fast-APEM) is an intelligent datasheet extraction tool 
    designed to automatically parse PDF product datasheets and extract technical specifications.</p>
    <p><strong>Key Features:</strong></p>
    <ul>
        <li>🐍 <strong>Python-First Extraction</strong> - Deterministic regex-based parsing for reliable results</li>
        <li>🤖 <strong>AI Enhancement</strong> - GPT-4o-mini fills gaps in low-confidence fields</li>
        <li>📊 <strong>Multi-Product Detection</strong> - Auto-detects LED indicators, joysticks, terminal blocks</li>
        <li>🔍 <strong>Confidence Tracking</strong> - Shows extraction quality per field</li>
        <li>📥 <strong>Excel Export</strong> - Download results individually or as ZIP</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown("## 👥 Development Team")

# Team member cards CSS
st.markdown("""
<style>
    .team-member-info {
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 0 0 12px 12px;
        text-align: center;
    }
    
    .team-member-name {
        color: white;
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0 0 0.25rem 0;
    }
    
    .team-member-role {
        color: rgba(255,255,255,0.85);
        font-size: 0.85rem;
        font-weight: 500;
        margin: 0;
    }
    
    /* Force consistent image height */
    .team-photo-container img {
        height: 280px !important;
        width: 100% !important;
        object-fit: cover !important;
        border-radius: 12px 12px 0 0;
    }
</style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="team-photo-container">', unsafe_allow_html=True)
    st.image("assets/team_alessandro.jpg", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="team-member-info">
        <p class="team-member-name">Alessandro Vigano</p>
        <p class="team-member-role">Business Intelligence Analyst</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown('<div class="team-photo-container">', unsafe_allow_html=True)
    st.image("assets/team_jad.jpg", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="team-member-info">
        <p class="team-member-name">Jad El Kattar</p>
        <p class="team-member-role">AI & Data Engineer</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown('<div class="team-photo-container">', unsafe_allow_html=True)
    st.image("assets/team_nikita.jpg", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="team-member-info">
        <p class="team-member-name">Nikita Marushko</p>
        <p class="team-member-role">QA & Testing Lead</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Tech Stack
st.markdown("## 🛠️ Technology Stack")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("### 🐍 Python")
    st.markdown("Core extraction logic with pdfplumber and regex")
with col2:
    st.markdown("### 🤖 OpenAI")
    st.markdown("GPT-4o-mini for AI enhancement")
with col3:
    st.markdown("### 🎨 Streamlit")
    st.markdown("Modern web interface")
with col4:
    st.markdown("### 📊 Pandas")
    st.markdown("Data processing & Excel export")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888;">
    © 2025 ScrAPEM Intelligence | Built by Jad El Kattar, Alessandro Vigano, Nikita Marushko | Powered by APEM
</div>
""", unsafe_allow_html=True)
