"""
Shared navigation component for ScrAPEM
Clean navbar: Logo left, text links right
"""
import streamlit as st

def render_navbar(current_page="Home"):
    """
    Render a consistent navigation bar at the top of each page.
    current_page: "Home", "Extractor", "About", or "Docs"
    """
    
    # Navbar CSS
    st.markdown("""
    <style>
        /* Hide Streamlit's default button styling for nav */
        .stButton > button {
            background: transparent !important;
            border: none !important;
            color: #374151 !important;
            font-weight: 500 !important;
            padding: 0 !important;
            font-size: 0.95rem !important;
        }
        
        .stButton > button:hover {
            color: #667eea !important;
            background: transparent !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Build navbar with columns: logo on left, links on right
    col_logo, col_spacer, col_home, col_about, col_docs, col_extractor = st.columns([2, 3, 0.7, 0.7, 0.7, 1.2])
    
    with col_logo:
        st.image("assets/apem_logo.png", width=130)
    
    with col_home:
        if current_page == "Home":
            st.markdown('<span style="color: #667eea; font-weight: 600;">🏠 Home</span>', unsafe_allow_html=True)
        else:
            if st.button("🏠 Home", key="nav_home"):
                st.switch_page("app.py")
    
    with col_about:
        if current_page == "About":
            st.markdown('<span style="color: #667eea; font-weight: 600;">ℹ️ About</span>', unsafe_allow_html=True)
        else:
            if st.button("ℹ️ About", key="nav_about"):
                st.switch_page("pages/2_ℹ️_About.py")
    
    with col_docs:
        if current_page == "Docs":
            st.markdown('<span style="color: #667eea; font-weight: 600;">📚 Docs</span>', unsafe_allow_html=True)
        else:
            if st.button("📚 Docs", key="nav_docs"):
                st.switch_page("pages/3_📚_Docs.py")
    
    with col_extractor:
        if current_page == "Extractor":
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 0.5rem 1rem; border-radius: 8px; 
                        font-weight: 600; text-align: center;">
                📄 Extractor
            </div>
            """, unsafe_allow_html=True)
        else:
            if st.button("🚀 Extractor", key="nav_extractor", type="primary"):
                st.switch_page("pages/1_📄_Extractor.py")
    
    st.markdown("")
