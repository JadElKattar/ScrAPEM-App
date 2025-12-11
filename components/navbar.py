"""
Shared navigation component for ScrAPEM
Clean navbar: Logo left, text links right
Uses st.switch_page for reliable navigation
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
        /* Reduce top padding */
        .main .block-container {
            padding-top: 0.25rem !important;
        }
        
        /* Button styling for nav ONLY - scoped to navbar area */
        .navbar-container .stButton > button {
            background: transparent !important;
            border: none !important;
            color: #374151 !important;
            font-weight: 500 !important;
            padding: 0.5rem 0.75rem !important;
            font-size: 0.95rem !important;
            border-radius: 6px !important;
        }
        
        .navbar-container .stButton > button:hover {
            color: #667eea !important;
            background: rgba(102, 126, 234, 0.1) !important;
        }
        
        /* Active nav styling */
        .nav-active-text {
            color: #667eea;
            font-weight: 600;
            background: rgba(102, 126, 234, 0.12);
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            display: inline-block;
        }
        
        /* CTA button */
        .nav-cta-active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-weight: 600;
            display: inline-block;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Build navbar with columns
    col_logo, col_spacer, col_home, col_about, col_docs, col_extractor = st.columns([1.5, 2.5, 0.8, 0.8, 0.8, 1])
    
    with col_logo:
        st.image("assets/apem_logo.png", width=130)
    
    with col_home:
        if current_page == "Home":
            st.markdown('<span class="nav-active-text">🏠 Home</span>', unsafe_allow_html=True)
        else:
            if st.button("🏠 Home", key="nav_home"):
                st.switch_page("app.py")
    
    with col_about:
        if current_page == "About":
            st.markdown('<span class="nav-active-text">ℹ️ About</span>', unsafe_allow_html=True)
        else:
            if st.button("ℹ️ About", key="nav_about"):
                st.switch_page("pages/2_ℹ️_About.py")
    
    with col_docs:
        if current_page == "Docs":
            st.markdown('<span class="nav-active-text">📚 Docs</span>', unsafe_allow_html=True)
        else:
            if st.button("📚 Docs", key="nav_docs"):
                st.switch_page("pages/3_📚_Docs.py")
    
    with col_extractor:
        if current_page == "Extractor":
            st.markdown('<span class="nav-cta-active">📄 Extractor</span>', unsafe_allow_html=True)
        else:
            if st.button("🚀 Extractor", key="nav_extractor", type="primary"):
                st.switch_page("pages/1_📄_Extractor.py")
    
    st.markdown("")
