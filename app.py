import streamlit as st
import pandas as pd
import os
import json
import re
import requests
import time
import plotly.express as px
from streamlit_lottie import st_lottie
from dotenv import load_dotenv
from groq import Groq

# --- 1. CONFIGURATION & SETUP ---

load_dotenv()

st.set_page_config(
    page_title="HirePilot",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "HirePilot: AI-Powered Job Search"
    }
)

# Configure Groq Client
api_key = os.getenv("GROQ_API_KEY")
GROQ_ENABLED = False

if api_key:
    try:
        client = Groq(api_key=api_key)
        GROQ_ENABLED = True
    except Exception as e:
        st.error(f"⚠️ Groq configuration error: {e}")

# Import our modules
try:
    from job_api import JobSearchAPI
    from job_matcher_simple import JobMatcher
    from resume_parser_simple import extract_text_from_pdf, extract_text_from_docx, clean_text
except ImportError as e:
    st.error(f"❌ Failed to import modules: {e}")
    st.stop()

# --- LOTTIE ANIMATION LOADER ---
@st.cache_data
def load_lottieurl(url: str):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# Load Assets
lottie_search = load_lottieurl("https://lottie.host/9d6d3765-a687-4389-a292-663290299f2e/F8Y1s2a2W4.json") 
lottie_success = load_lottieurl("https://lottie.host/020cc9c9-7e2b-426c-9426-3d2379d76c94/Jg57s8c5Q8.json") 
lottie_upload = load_lottieurl("https://lottie.host/2c1df74b-a19c-4ce4-8eb3-ee2ff88e5ffb/XA4W6IzcWS.json")

# --- 2. CSS STYLING (GPU ACCELERATED ANIMATIONS) ---
st.markdown("""
<style>
    /* CSS Variables for System Adaptability */
    :root {
        --orange-brand: #f97316;
        --orange-light: rgba(249, 115, 22, 0.1);
        --orange-border: rgba(249, 115, 22, 0.3);
        --gray-border: rgba(128, 128, 128, 0.3);
        /* Streamlit native variables */
        --card-bg: var(--secondary-background-color); 
        --text-main: var(--text-color);
    }

    /* --- ANIMATION KEYFRAMES (OPTIMIZED) --- */
    
    /* 1. Background Liquid Flow */
    @keyframes liquid-flow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* 2. Banner Entrance Slide (Uses Margin) */
    @keyframes slide-in-top {
        0% {
            margin-top: -150px;
            opacity: 0;
        }
        100% {
            margin-top: 0;
            opacity: 1;
        }
    }

    /* 3. Content Fade In Up (For everything else) */
    @keyframes fade-in-up {
        0% {
            opacity: 0;
            transform: translateY(20px);
        }
        100% {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* 4. Floating Levitation */
    @keyframes levitate-smooth {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
        100% { transform: translateY(0px); }
    }

    /* 5. Text Glow Pulse */
    @keyframes text-glow-pulse {
        0% { text-shadow: 0 0 5px rgba(249, 115, 22, 0.2); }
        50% { text-shadow: 0 0 20px rgba(249, 115, 22, 0.6), 0 0 10px rgba(249, 115, 22, 0.4); }
        100% { text-shadow: 0 0 5px rgba(249, 115, 22, 0.2); }
    }

    /* Top Banner - "HirePilot" Style with Slide Entrance */
    .top-banner {
        text-align: center; 
        padding: 5rem 0; 
        
        /* Modern Tech Gradient */
        background: linear-gradient(120deg, #ea580c, #c2410c, #7c3aed, #4f46e5);
        background-size: 200% 200%;
        
        /* Shape */
        border-radius: 0 0 50px 50px; 
        margin-bottom: 4rem; 
        
        /* COMBINED ANIMATION:
           1. slide-in-top: Runs once for 1.2s (Entrance)
           2. liquid-flow: Runs forever
           3. levitate-smooth: Runs forever
        */
        animation: 
            slide-in-top 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94) both,
            liquid-flow 20s ease infinite,
            levitate-smooth 6s ease-in-out infinite;
            
        will-change: background-position, transform, margin-top;
        
        position: relative;
        z-index: 10;
        
        /* Shadow */
        box-shadow: 0 25px 50px -12px rgba(79, 70, 229, 0.4);
    }
    
    .top-banner h1 {
        color: white !important; 
        margin: 0; 
        font-size: 4.5rem; 
        font-weight: 800;
        text-shadow: 0 4px 15px rgba(0,0,0,0.3); 
        letter-spacing: -2px;
    }
    
    .top-banner p {
        color: rgba(255,255,255,0.85) !important; 
        margin-top: 0.5rem; 
        font-size: 1.1rem; 
        font-weight: 500;
        letter-spacing: 1px;
        text-transform: uppercase;
        opacity: 0.9;
    }

    /* Footer Text Glow (White Text + Brand Colored Shadow) */
    .footer-container {
        text-align: center;
        padding: 1.2rem;
        margin-top: 3rem;
        margin-bottom: 2rem;
        font-weight: 700;
        font-size: 1.1rem;
        letter-spacing: 0.5px;
        color: #ffffff;
        text-shadow: 0 0 15px rgba(234, 88, 12, 0.5), 0 0 30px rgba(124, 58, 237, 0.4);
        animation: text-glow-pulse 4s ease-in-out infinite;
    }

    /* Step Headers with GLOW Animation + FADE IN ENTRANCE */
    .step-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-main);
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
        
        /* Combined Animation: 
           1. fade-in-up: Entrance (Delays 0.8s to start after banner)
           2. text-glow-pulse: Infinite glow 
        */
        animation: 
            fade-in-up 0.8s ease-out 0.8s backwards, 
            text-glow-pulse 3s ease-in-out infinite;
    }
    .step-number {
        background: linear-gradient(135deg, #ea580c, #f97316);
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        font-weight: 800;
        box-shadow: 0 4px 10px rgba(234, 88, 12, 0.3);
    }

    /* Job Card Container & Upload Area - FADE IN AFTER HEADER */
    .job-card {
        background-color: var(--card-bg);
        border-radius: 24px;
        padding: 3rem;
        margin: 2.5rem 0;
        border: 1px solid var(--gray-border); /* Neutral gray border */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.2s, box-shadow 0.2s;
        will-change: transform;
        
        /* Entrance: Wait 1.0s, then float up */
        animation: fade-in-up 0.8s ease-out 1.0s backwards;
    }
    .job-card:hover {
        border-color: var(--orange-brand); /* Orange pop on hover */
        transform: translateY(-5px);
        box-shadow: 0 15px 30px -5px rgba(249, 115, 22, 0.15);
    }

    /* Text & Headers */
    .job-title {
        color: var(--text-main);
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
    }
    .company-name {
        color: var(--text-main);
        opacity: 0.8;
        font-size: 1.4rem;
        font-weight: 500;
        margin-top: 0.5rem;
    }
    .section-title {
        color: var(--orange-brand); 
        font-size: 1.1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 800;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        border-bottom: 2px solid var(--orange-border);
        padding-bottom: 0.5rem;
    }
    .summary-text {
        font-size: 1.1rem;
        line-height: 1.8;
        color: var(--text-main);
        margin-bottom: 2rem;
        font-weight: 400;
    }

    /* Lists */
    ul.clean-list { list-style-type: none; padding: 0; margin: 0; }
    ul.clean-list li {
        position: relative;
        padding-left: 2rem;
        margin-bottom: 1rem;
        color: var(--text-main);
        font-size: 1rem;
        line-height: 1.6;
        opacity: 0.9;
    }
    ul.clean-list li::before {
        content: "🔹"; 
        position: absolute;
        left: 0;
        font-size: 0.9rem;
        color: var(--orange-brand);
    }

    /* Tech Stack Badges */
    .tech-tag {
        display: inline-block;
        background: var(--card-bg);
        color: var(--orange-brand);
        border: 1px solid var(--orange-border);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-family: monospace;
        font-size: 0.9rem;
        font-weight: 700;
        margin: 0 0.5rem 0.5rem 0;
    }

    /* Soft Skill Badges */
    .soft-tag {
        display: inline-block;
        background: var(--orange-light);
        color: var(--text-main);
        border: 1px solid var(--orange-border);
        padding: 0.4rem 1rem;
        border-radius: 99px;
        font-size: 0.9rem;
        margin: 0 0.5rem 0.5rem 0;
    }

    /* Culture/Benefits Box */
    .culture-box {
        background: linear-gradient(135deg, rgba(249, 115, 22, 0.05) 0%, rgba(251, 191, 36, 0.05) 100%);
        border: 1px solid var(--orange-border);
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1.5rem;
    }

    /* AI Insight Section */
    .ai-insight-card {
        background: var(--card-bg); 
        border-radius: 16px;
        padding: 2rem;
        margin-top: 2rem;
        border: 1px solid var(--orange-border);
        animation: fadeIn 0.5s;
    }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

    /* Score Badge */
    .score-badge {
        background: var(--card-bg);
        border: 2px solid;
        border-radius: 20px;
        padding: 1.5rem;
        text-align: center;
        min-width: 120px;
    }
    .score-val { font-size: 2.8rem; font-weight: 900; line-height: 1; margin-bottom: 0.2rem; color: var(--text-main); }
    .score-lbl { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-main); opacity: 0.7; }
    
    .high-match { color: #10b981; border-color: #10b981; }
    .med-match { color: #f59e0b; border-color: #f59e0b; }
    .low-match { color: #ef4444; border-color: #ef4444; }

    /* Meta Badges (Static Information) */
    .meta-container {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        margin-bottom: 2.5rem;
    }
    .meta-badge {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding: 0.6rem 1.2rem;
        border-radius: 50px; /* More rounded/pill shape */
        font-size: 0.95rem;
        font-weight: 500;
        background: rgba(128,128,128, 0.1); /* Neutral background */
        border: 1px solid rgba(128,128,128, 0.2);
        color: var(--text-main);
        opacity: 0.9;
    }

    /* Cover Letter Paper UI */
    .paper-doc {
        background-color: #ffffff;
        color: #1e293b;
        padding: 3rem;
        border-radius: 2px;
        font-family: 'Times New Roman', serif;
        line-height: 1.6;
        white-space: pre-wrap;
        margin-top: 1rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
        font-size: 1.05rem;
    }
    .paper-header {
        border-bottom: 1px solid #cbd5e1;
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
        font-family: 'Arial', sans-serif;
        color: #334155;
        font-size: 0.9rem;
    }

    /* ACTION BUTTONS (Analyze / Draft) - Enhanced Look */
    .stButton > button {
        background-color: transparent !important;
        border: 2px solid var(--orange-border) !important;
        color: var(--text-main) !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05) !important;
    }
    .stButton > button:hover {
        border-color: var(--orange-brand) !important;
        color: var(--orange-brand) !important;
        background-color: var(--orange-light) !important;
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(249, 115, 22, 0.2) !important;
    }

    /* APPLY BUTTON (Primary) - Gradient Style */
    .stLinkButton > a {
        background: linear-gradient(90deg, #ea580c 0%, #f97316 100%) !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 0.7rem 2rem !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        text-align: center !important;
        text-decoration: none !important;
        display: block !important;
        border: none !important;
        box-shadow: 0 10px 15px -3px rgba(234, 88, 12, 0.4) !important;
        transition: transform 0.2s !important;
    }
    .stLinkButton > a:hover {
        transform: translateY(-2px) !important;
        background: linear-gradient(90deg, #c2410c 0%, #ea580c 100%) !important;
    }

    /* --- MOBILE OPTIMIZATIONS --- */
    @media (max-width: 768px) {
        .top-banner h1 { font-size: 2.5rem !important; }
        .job-card { padding: 1.5rem !important; margin: 1.5rem 0 !important; border-radius: 16px !important; }
        .job-title { font-size: 1.6rem !important; }
        .score-badge { padding: 0.8rem !important; min-width: 80px !important; margin-top: 1rem; }
        .score-val { font-size: 2rem !important; }
        .meta-container { gap: 0.5rem !important; }
        .meta-badge { padding: 0.5rem 1rem !important; font-size: 0.85rem !important; width: 100%; justify-content: center; }
        .stButton > button { width: 100% !important; margin-bottom: 0.5rem !important; }
        .stLinkButton > a { width: 100% !important; text-align: center !important; }
        .paper-doc { padding: 1.5rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- 3. GROQ AI HELPER FUNCTIONS ---

@st.cache_data(show_spinner=False, ttl=3600)
def get_ai_analysis(job_description, job_title, employer_name):
    if not GROQ_ENABLED: return {"summary": "⚠️ API Key missing."}
    
    desc_text = str(job_description).strip().replace("{", "(").replace("}", ")").replace('"', "'")
    
    try:
        system_prompt = "You are a Senior Technical Recruiter. Analyze job descriptions deeply."
        user_prompt = f"""
        Analyze this job posting for "{job_title}" at "{employer_name}".
        
        Return a valid JSON object (AND NOTHING ELSE) with these specific keys:
        {{
            "summary": "3-4 sentence executive summary.",
            "role_intent": "Why they are hiring (1 sentence).",
            "tech_stack": ["List tools/languages"],
            "soft_skills": ["List soft skills"],
            "key_responsibilities": ["4-5 daily duties"],
            "requirements": ["4-5 qualifications"],
            "education_cert": "Education/Certs",
            "remote_policy": "Remote/Hybrid status",
            "salary_benefits": "Salary and perks",
            "culture_vibe": "Company culture"
        }}
        Job Description: {desc_text[:15000]}
        """
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.1,
            max_tokens=2000,
        )
        
        response_text = completion.choices[0].message.content
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            return json.loads(response_text[start_idx : end_idx + 1])
        return {"summary": "⚠️ AI output format error."}
    except Exception as e:
        return {"summary": f"⚠️ Groq Error: {str(e)[:200]}"}

@st.cache_data(show_spinner=False, ttl=3600)
def generate_cover_letter(resume_text, job_description, job_title, employer_name):
    """
    Generates a high-quality, 4-paragraph evidence-based cover letter.
    """
    if not GROQ_ENABLED: return "⚠️ Enable AI to generate cover letter."
    try:
        system_prompt = """
        You are an elite Career Strategist and Professional Copywriter.
        Your goal is to write a cover letter that is persuasive, human, and focuses on "Value Fit" and "Motivation".
        Do NOT be robotic. Do NOT provide conversational filler (e.g. "Here is the letter").
        """
        
        user_prompt = f"""
        Write a high-impact cover letter for the role of "{job_title}" at "{employer_name}".
        
        RESUME CONTENT:
        {resume_text[:15000]}
        
        JOB DESCRIPTION:
        {job_description[:10000]}
        
        ### 1. HEADER FORMAT (Strictly Follow This):
        
        [Candidate Name]
        [Candidate Email] | [Candidate Phone]
        
        [Current Date]
        
        {employer_name}
        [Company Address or "Headquarters"]
        
        Dear Hiring Manager,
        
        ### 2. CRITICAL RULES:
        * **EXTRACT REAL DATA:** Use the Name, Phone, and Email found in the resume content. Do NOT use placeholders like "[Your Name]" unless the data is completely missing.
        * **NO "JOHN":** Never invent a name. If name is missing, use "[Your Name]".
        * **FIX CASING:** Auto-correct names to Title Case (e.g. "TAN RIHAO" -> "Tan Rihao").
        * **NO MARKDOWN LINKS:** Write email as plain text (e.g. email@example.com).
        
        ### 3. BODY STRUCTURE (Strictly 4 Paragraphs):
        * **PARAGRAPH 1 (The Hook):** Introduce yourself by name and degree/university. State you are applying for **{job_title}** at **{employer_name}**. Mention why you admire the company (based on JD).
        * **PARAGRAPH 2 (The Hard Skills):** Select 1-2 specific achievements from your resume that directly prove you can solve their key requirements. Use numbers.
        * **PARAGRAPH 3 (Motivation & Culture):** Discuss your work ethic and "Why" you are a good culture fit. Connect personal values to company mission.
        * **PARAGRAPH 4 (Closing):** Reiterate enthusiasm and include a confident call to action for an interview.
        * **SIGN-OFF:** End with "Sincerely," followed by a newline and the [Candidate Name].
        """
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.7,
            max_tokens=1500,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error: {e}"

# --- 4. APP STATE ---
if 'resume_text' not in st.session_state: st.session_state.resume_text = ""
if 'jobs_df' not in st.session_state: st.session_state.jobs_df = pd.DataFrame()
if 'matches_df' not in st.session_state: st.session_state.matches_df = pd.DataFrame()
if 'resume_uploaded' not in st.session_state: st.session_state.resume_uploaded = False
if 'last_uploaded_file' not in st.session_state: st.session_state.last_uploaded_file = None
if 'ai_results' not in st.session_state: st.session_state.ai_results = {} 
if 'cover_letters' not in st.session_state: st.session_state.cover_letters = {}
if 'search_stats' not in st.session_state: st.session_state.search_stats = {
    'searches': 0, 'matches_found': 0, 'avg_score': 0
}

# --- 5. ANIMATED UI COMPONENTS ---

def create_match_visualization(match_score):
    """Create optimized gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=match_score,
        number={'suffix': "%", 'font': {'size': 30, 'color': "white"}},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [None, 100], 'visible': False},
            'bar': {'color': "#ff6b00"},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 100], 'color': 'rgba(255,255,255,0.1)'}
            ],
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=20, b=20),
        height=150
    )
    return fig

# --- 6. MAIN UI LAYOUT ---

# Top Banner
st.markdown("""
<div class='top-banner'>
    <h1>HirePilot</h1>
    <p>powered by Groq Llama 3.1</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    with st.expander("🐣 Quick Start Guide", expanded=True):
        st.markdown("""
        **1. Upload:** Upload resume in Step 1.
        
        **2. Search:** Enter Job & Location in Step 2.
        
        **3. Results:** View matches, Deep Dive, and Apply below.
        """)
    
    st.markdown("---")
    
    if st.session_state.resume_uploaded:
        if st.button("🗑️ Reset / New Resume"):
            st.session_state.resume_text = ""
            st.session_state.resume_uploaded = False
            st.session_state.matches_df = pd.DataFrame()
            st.session_state.jobs_df = pd.DataFrame()
            st.rerun()

# --- STEP 1: UPLOAD RESUME ---
st.markdown('<div class="step-header"> Upload Your Resume</div>', unsafe_allow_html=True)

if not st.session_state.resume_uploaded:
    uploaded_file = st.file_uploader("Upload PDF or DOCX", type=['pdf', 'docx'], label_visibility="collapsed")
    
    if uploaded_file and (st.session_state.last_uploaded_file != uploaded_file.name):
        progress_text = "Analyzing Profile..."
        my_bar = st.progress(0, text=progress_text)
        
        try:
            # Simulate progress for smoother feel
            for percent in range(0, 101, 20):
                time.sleep(0.05)
                my_bar.progress(percent, text=progress_text)
            
            if uploaded_file.name.endswith('.pdf'):
                text = extract_text_from_pdf(uploaded_file)
            else:
                text = extract_text_from_docx(uploaded_file)
            
            if text and len(clean_text(text)) > 50:
                st.session_state.resume_text = clean_text(text)
                st.session_state.resume_uploaded = True
                st.session_state.last_uploaded_file = uploaded_file.name
                
                my_bar.empty()
                if lottie_upload:
                    st_lottie(lottie_upload, height=150, key="upload_anim", loop=False)
                st.toast("✅ Resume uploaded successfully!", icon="✨")
                time.sleep(1)
                st.rerun()
            else:
                my_bar.empty()
                st.error("❌ File empty or unreadable.")
        except Exception as e:
            my_bar.empty()
            st.error(f"Error: {e}")
else:
    with st.expander("✅ Resume Uploaded", expanded=False):
        st.success("Resume is loaded and ready for matching.")
        if st.button("Upload Different Resume"):
            st.session_state.resume_uploaded = False
            st.rerun()

# --- STEP 2: SEARCH JOBS ---
if st.session_state.resume_uploaded:
    st.markdown("---")
    st.markdown('<div class="step-header"> Find Your Dream Job</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        job_title = st.text_input("Job Title", placeholder="e.g. Software Engineer")
    with col2:
        location = st.text_input("Location", placeholder="e.g. Singapore, Remote")
    with col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) 
        search_btn = st.button("🚀 Find Matches", use_container_width=True, type="primary")

    if search_btn:
        if lottie_search:
            st_lottie(lottie_search, height=200, key="search_loader")
        else:
            with st.spinner("🔍 Searching..."):
                pass

        try:
            api = JobSearchAPI()
            jobs = api.search_jobs(query=job_title, location=location, num_pages=1)
            
            if not jobs.empty:
                st.session_state.jobs_df = jobs
                st.session_state.ai_results = {} 
                st.session_state.cover_letters = {}
                matcher = JobMatcher()
                matches = matcher.match_resume_to_jobs(
                    st.session_state.resume_text, st.session_state.jobs_df, top_n=10
                )
                st.session_state.matches_df = matches
                st.rerun()
            else:
                st.session_state.matches_df = pd.DataFrame() 
                st.error("❌ No jobs found. Try a broader search term.")
        except Exception as e:
            st.error(f"System Error: {str(e)}")

# --- STEP 3: MATCHED RESULTS ---
if not st.session_state.matches_df.empty:
    st.markdown("---")
    st.markdown('<div class="step-header"> Matched Roles</div>', unsafe_allow_html=True)
    
    if lottie_success:
        st_lottie(lottie_success, height=120, key="success_anim", loop=False)
    
    st.success(f"🎉 Found {len(st.session_state.matches_df)} jobs matching your resume!")

    # --- PLOTLY: MARKET INSIGHTS ---
    # Create a simple salary distribution chart if salary data exists
    valid_salaries = st.session_state.matches_df[st.session_state.matches_df['salary_min'].notnull()]
    if not valid_salaries.empty:
        try:
            fig = px.bar(
                valid_salaries, 
                x='employer_name', 
                y='salary_min', 
                color='match_score',
                title='💰 Market Salary Analysis (Min Base)',
                labels={'salary_min': 'Minimum Salary ($)', 'employer_name': 'Company'},
                color_continuous_scale='Oranges'
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#ffffff'
            )
            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            pass # Skip chart if error

    for idx, row in st.session_state.matches_df.iterrows():
        score = row.get('match_score', 0)
        job_desc = row.get('job_description', '')
        job_title_txt = row.get('job_title', 'Job')
        employer = row.get('employer_name', 'Company')
        location_txt = row.get('location_display', 'Remote')
        job_id = row.get('job_id', f"job_{idx}")
        
        # Determine colors for score
        if score >= 80:
            score_class = "high-match"
        elif score >= 60:
            score_class = "med-match"
        else:
            score_class = "low-match"
        
        # --- RENDER JOB CARD ---
        st.markdown(f'<div class="job-card">', unsafe_allow_html=True)
        
        # Header Row
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.markdown(f"<div class='job-title'>{job_title_txt}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='company-name'>🏢 {employer}</div>", unsafe_allow_html=True)
        
        with col_b:
            st.markdown(f"""
            <div class='score-badge {score_class}'>
                <div class='score-val'>{score:.0f}%</div>
                <div class='score-lbl'>Match</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        # Meta Badges
        st.markdown(f"""
        <div class='meta-container'>
            <div class='meta-badge'>📍 {location_txt}</div>
            <div class='meta-badge'>💼 {row.get('job_employment_type', 'Full-time')}</div>
            <div class='meta-badge'>🏭 {row.get('industry', 'Tech')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # AI Insights
        ai_data = st.session_state.ai_results.get(job_id)
        
        if ai_data:
            if "⚠️" not in ai_data.get('summary', ''):
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.05); padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="color: #ff6b00; font-weight: 800; margin-bottom: 0.5rem; text-transform: uppercase;">📝 Executive Summary</div>
                    <div style="color: #cbd5e1; line-height: 1.6;">{ai_data.get('summary')}</div>
                </div>
                """, unsafe_allow_html=True)
                
                tech = ai_data.get('tech_stack', [])
                if tech:
                    tech_html = "".join([f'<span class="tech-tag">{t}</span>' for t in tech[:8]])
                    st.markdown(f"<div style='margin-bottom: 1.5rem;'>{tech_html}</div>", unsafe_allow_html=True)
                
                col_l, col_r = st.columns(2)
                with col_l:
                    reqs = ai_data.get('key_responsibilities', [])
                    if reqs:
                        list_html = "".join([f'<li style="margin-bottom:0.5rem;">{r}</li>' for r in reqs[:4]])
                        st.markdown(f"<div style='color:#ff6b00; font-weight:700; margin-bottom:0.5rem;'>📋 Responsibilities</div><ul style='color:#cbd5e1; padding-left:1.2rem;'>{list_html}</ul>", unsafe_allow_html=True)
                with col_r:
                    must_haves = ai_data.get('requirements', [])
                    if must_haves:
                        list_html = "".join([f'<li style="margin-bottom:0.5rem;">{r}</li>' for r in must_haves[:4]])
                        st.markdown(f"<div style='color:#00f3ff; font-weight:700; margin-bottom:0.5rem;'>✅ Requirements</div><ul style='color:#cbd5e1; padding-left:1.2rem;'>{list_html}</ul>", unsafe_allow_html=True)
            else:
                st.error(ai_data.get('summary'))
        else:
            col_x, col_y = st.columns(2)
            with col_x:
                if st.button(f"✨ AI Deep Dive", key=f"ai_{idx}", use_container_width=True):
                    if GROQ_ENABLED:
                        with st.spinner("🤖 Analyzing job details..."):
                            result = get_ai_analysis(job_desc, job_title_txt, employer)
                            st.session_state.ai_results[job_id] = result
                            st.rerun()
                    else:
                        st.warning("⚠️ Add GROQ_API_KEY to .env")

        # Cover Letter
        cl_text = st.session_state.cover_letters.get(job_id)
        if cl_text:
            st.markdown(f"""
            <div style="background: #fdfbf7; color: #1e293b; padding: 2rem; border-radius: 4px; margin: 1.5rem 0; font-family: 'Times New Roman', serif;">
                <div style="border-bottom: 1px solid #cbd5e1; padding-bottom: 0.5rem; margin-bottom: 1rem; font-family: sans-serif; font-size: 0.8rem; color: #64748b;">DRAFT PREVIEW</div>
                <div style="white-space: pre-wrap; font-size: 1rem; line-height: 1.6;">{cl_text[:600]}...</div>
            </div>
            """, unsafe_allow_html=True)

        # Buttons
        st.markdown("<div style='margin-top: 1.5rem;'>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns([1, 1])
        
        with col_btn1:
            lbl = "✍️ Write Cover Letter" if not cl_text else "🔄 Regenerate Letter"
            if st.button(lbl, key=f"cl_{idx}", use_container_width=True):
                if GROQ_ENABLED:
                    with st.spinner("Writing..."):
                        letter = generate_cover_letter(st.session_state.resume_text, job_desc, job_title_txt, employer)
                        st.session_state.cover_letters[job_id] = letter
                        st.rerun()
                else:
                    st.warning("Enable AI first")
        
        with col_btn2:
            if row.get('job_apply_link'):
                st.link_button("🚀 Apply Now", row['job_apply_link'], use_container_width=True)
        
        st.markdown("</div></div>", unsafe_allow_html=True) # End Job Card

# Footer
st.markdown("---")
st.markdown("""
<div class='footer-container'>
    Turn skills into offers • Automate Your Job Search
</div>
""", unsafe_allow_html=True)