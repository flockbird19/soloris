import streamlit as st
import requests
from pathlib import Path
from streamlit_lottie import st_lottie

# Import your core logic
from mcp_server import setup_identity, live_gmail_scan, generate_bereavement_package
from agent import context
from tools import LogisticsManager

# --- PAGE CONFIG ---
st.set_page_config(page_title="GriefOS", page_icon="🕊️", layout="wide")

# --- THE "CLEAN WEB" CSS OVERRIDE ---
st.markdown("""
    <style>
    /* Import modern typography */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #F9FAFB;
    }

    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 30px;
        box-shadow: 0 10px 40px -10px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }

    /* Gradient Hero Section */
    .hero-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 60px;
        border-radius: 30px;
        color: white;
        text-align: center;
        margin-bottom: 40px;
    }

    /* Custom Buttons */
    .stButton>button {
        background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 12px;
        font-weight: 600;
        transition: transform 0.2s ease;
        width: 100%;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(124, 58, 237, 0.4);
    }

    /* Modern Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: white;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
        padding: 0 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- ANIMATION LOADER ---
def load_lottie(url):
    try:
        return requests.get(url).json()
    except:
        return None

lottie_hero = load_lottie("https://lottie.host/80860534-1901-4433-8742-f8c7d6b0544b/uVqj4FqYsh.json")

# --- APP LAYOUT ---
# 1. HERO SECTION
st.markdown("""
    <div class="hero-section">
        <h1 style='font-size: 3.5rem; font-weight: 800; margin-bottom: 10px;'>🕊️ GriefOS</h1>
        <p style='font-size: 1.2rem; opacity: 0.9;'>Automating the administrative burden of loss with Compassionate AI.</p>
    </div>
    """, unsafe_allow_html=True)

# 2. MAIN WORKFLOW
col_left, col_right = st.columns([0.65, 0.35], gap="large")

with col_left:
    tabs = st.tabs(["📄 Identity", "🔍 Asset Discovery", "🗺️ Roadmap"])
    
    # --- IDENTITY TAB ---
    with tabs[0]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Document Verification")
        uploaded_file = st.file_uploader("Upload Death Certificate (PDF/JPG)", type=['pdf', 'jpg', 'png'], label_visibility="collapsed")
        
        if uploaded_file:
            temp_p = Path(f"temp_{uploaded_file.name}")
            with open(temp_p, "wb") as f: f.write(uploaded_file.getbuffer())
            
            if st.button("Verify Certificate"):
                with st.spinner("AI is analyzing the certificate..."):
                    msg = setup_identity(str(temp_p.absolute()))
                    st.toast(msg)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ASSET TAB ---
    with tabs[1]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Digital Footprint Search")
        st.write("Our MCP server scans Gmail for financial markers and legal footprints.")
        if st.button("Initiate Deep Scan"):
            with st.spinner("Decoding financial records from Gmail..."):
                res = live_gmail_scan()
                st.write(res)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ROADMAP TAB ---
    with tabs[2]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Generated Action Plan")
        if st.button("Finalize Bereavement Package"):
            package_msg = generate_bereavement_package()
            st.balloons()
            st.success("Your dossiers are ready for download.")
        
        if context.tasks:
            for task in context.tasks:
                st.checkbox(task.title, key=f"ui_{task.task_id}")
        st.markdown('</div>', unsafe_allow_html=True)

# 3. SIDEBAR / SUMMARY
with col_right:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    if lottie_hero:
        st_lottie(lottie_hero, height=200)
    
    st.markdown("### **Case Details**")
    if context.identity:
        st.markdown(f"""
            <div style="background: #F3F4F6; padding: 15px; border-radius: 12px; margin-top: 10px;">
                <p style="margin:0; font-size: 0.8rem; color: #6B7280;">DECEASED</p>
                <p style="margin:0; font-weight: 700; font-size: 1.1rem;">{context.identity.deceased_name}</p>
                <p style="margin:10px 0 0 0; font-size: 0.8rem; color: #6B7280;">DOD</p>
                <p style="margin:0; font-weight: 700;">{context.identity.date_of_death}</p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No identity verified yet.")
    
    st.divider()
    
    st.markdown("### **Discovery Stats**")
    c1, c2 = st.columns(2)
    c1.metric("Assets", len(context.assets))
    c2.metric("Tasks", len(context.tasks))
    
    # Logistics
    lm = LogisticsManager()
    st.caption(lm.calculate_photocopy_needs(context.tasks))
    st.markdown('</div>', unsafe_allow_html=True)