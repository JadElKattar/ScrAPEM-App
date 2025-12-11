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
    .team-member-card {
        background: #1a1a2e;
        border-radius: 12px;
        overflow: hidden;
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .team-member-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    
    .team-member-photo {
        width: 100%;
        height: 250px;
        object-fit: cover;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .team-member-info {
        padding: 1.25rem;
        background: #1a1a2e;
    }
    
    .team-member-name {
        color: white;
        font-size: 1.2rem;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
    }
    
    .team-member-role {
        color: #a0a0a0;
        font-size: 0.9rem;
        font-weight: 500;
    }
    
    .placeholder-avatar {
        width: 100%;
        height: 250px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 4rem;
    }
</style>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.image("assets/team_jad.png", use_container_width=True)
    st.markdown("""
    <div class="team-member-info">
        <p class="team-member-name">Jad El Kattar</p>
        <p class="team-member-role">AI & Data Engineer</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.image("assets/team_alessandro.jpg", use_container_width=True)
    st.markdown("""
    <div class="team-member-info">
        <p class="team-member-name">Alessandro Vigano</p>
        <p class="team-member-role">Business Intelligence Analyst</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    # Placeholder for Nikita
    st.markdown("""
    <div class="placeholder-avatar">👤</div>
    """, unsafe_allow_html=True)
    st.markdown("""
    <div class="team-member-info">
        <p class="team-member-name">Nikita Marushko</p>
        <p class="team-member-role">QA & Testing Lead</p>
    </div>
    """, unsafe_allow_html=True)

# University info
st.markdown("")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("""
    <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; color: white;">
        <h4 style="margin: 0;">🎓 TBS Education | 2025-2026</h4>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Academic collaboration with APEM</p>
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
