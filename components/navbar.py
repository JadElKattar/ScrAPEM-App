"""
Shared navigation component for ScrAPEM
Clean navbar: Logo left, text links right
Uses URL-based navigation for Streamlit Cloud compatibility
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
            padding-top: 0.5rem !important;
        }
        
        /* Navbar link styles */
        .nav-link {
            color: #374151;
            text-decoration: none;
            font-weight: 500;
            font-size: 0.95rem;
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            transition: all 0.2s ease;
            display: inline-block;
        }
        
        .nav-link:hover {
            color: #667eea;
            background: rgba(102, 126, 234, 0.1);
        }
        
        .nav-link.active {
            color: #667eea;
            font-weight: 600;
            background: rgba(102, 126, 234, 0.12);
        }
        
        .nav-cta {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-weight: 600;
            text-decoration: none;
            display: inline-block;
            transition: all 0.2s ease;
        }
        
        .nav-cta:hover {
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
            transform: translateY(-1px);
        }
        
        .nav-cta.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        }
        
        .navbar-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.5rem 0;
            margin-bottom: 0.5rem;
        }
        
        .navbar-links {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Determine active states
    home_class = "nav-link active" if current_page == "Home" else "nav-link"
    about_class = "nav-link active" if current_page == "About" else "nav-link"
    docs_class = "nav-link active" if current_page == "Docs" else "nav-link"
    extractor_class = "nav-cta active" if current_page == "Extractor" else "nav-cta"
    
    # Build navbar using HTML for proper alignment
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image("assets/apem_logo.png", width=130)
    
    with col2:
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; align-items: center; gap: 0.5rem; height: 100%; padding-top: 0.5rem;">
            <a href="/" target="_self" class="{home_class}">🏠 Home</a>
            <a href="/About" target="_self" class="{about_class}">ℹ️ About</a>
            <a href="/Docs" target="_self" class="{docs_class}">📚 Docs</a>
            <a href="/Extractor" target="_self" class="{extractor_class}">🚀 Extractor</a>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("")
