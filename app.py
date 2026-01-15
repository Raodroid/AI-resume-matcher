import streamlit as st
import pandas as pd
import os
import json
import re
from dotenv import load_dotenv
from groq import Groq

# --- 1. CONFIGURATION & SETUP ---

load_dotenv()

st.set_page_config(
    page_title="Resume Matcher Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
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

# --- 2. CSS STYLING (SYSTEM THEME ADAPTIVE + ORANGE BRANDING) ---
st.markdown("""
<style>
    /* CSS Variables for System Adaptability */
    :root {
        --orange-brand: #f97316;
        --orange-light: rgba(249, 115, 22, 0.1);
        --orange-border: rgba(249, 115, 22, 0.3);
        --gray-border: rgba(128, 128, 128, 0.4); /* New Gray Border */
        /* Streamlit native variables */
        --card-bg: var(--secondary-background-color); 
        --text-main: var(--text-color);
    }

    /* Top Banner */
    .top-banner {
        text-align: center; 
        padding: 4rem 0; 
        background: linear-gradient(135deg, #ea580c 0%, #f97316 50%, #fbbf24 100%); 
        border-radius: 0 0 40px 40px; 
        margin-bottom: 3rem; 
        box-shadow: 0 20px 40px -10px rgba(249, 115, 22, 0.4);
    }
    .top-banner h1 {
        color: white !important; 
        margin: 0; 
        font-size: 4rem; 
        text-shadow: 0 4px 8px rgba(0,0,0,0.2); 
        letter-spacing: -1px;
    }
    .top-banner p {
        color: rgba(255,255,255,0.95) !important; 
        margin-top: 1rem; 
        font-size: 1.4rem; 
        font-weight: 500;
    }

    /* Job Card Container - GRAY BORDER ADDED */
    .job-card {
        background-color: var(--card-bg);
        border-radius: 24px;
        padding: 3rem;
        margin: 2.5rem 0;
        border: 1px solid var(--gray-border); /* Distinct Gray Border */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s, border-color 0.2s;
    }
    .job-card:hover {
        border-color: var(--orange-brand); /* Turns Orange on Hover */
        transform: translateY(-3px);
        box-shadow: 0 10px 20px -5px rgba(0,0,0,0.1);
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

    /* Meta Badges */
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
        padding: 0.7rem 1.4rem;
        border-radius: 12px;
        font-size: 1rem;
        font-weight: 600;
        background: var(--card-bg);
        border: 1px solid rgba(128,128,128, 0.2);
        color: var(--text-main);
    }

    /* Cover Letter Paper UI (Always White) */
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

    /* Buttons */
    .stLinkButton > a {
        background: linear-gradient(90deg, #ea580c 0%, #f97316 100%) !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 1rem 2rem !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
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
        
        ### 1. HEADER RULES:
        * **CLEAN DATA:** Extract the candidate's Name, Email, and Phone from the resume. 
        * **NO BRACKETS:** Write `Tan Rihao`, NOT `[Tan Rihao]`. Only use brackets if data is missing.
        * **FIX CASING:** Auto-correct name casing (e.g. `TAN RIHAO` -> `Tan Rihao`).
        * **NO MARKDOWN LINKS:** Write email as plain text `email@example.com`, NOT `[Email](mailto:...)`.
        
        ### 2. CONTENT STRUCTURE (Strictly 3-4 Paragraphs):
        * **PARAGRAPH 1 (The Introduction):** Introduce yourself by name and your specific degree/university. Explicitly state you are applying for the **{job_title}** role at **{employer_name}**. Show immediate professional confidence.
        * **PARAGRAPH 2 (The Evidence / Hard Skills):** Connect specific technical achievements from the resume to the core requirements in the JD. Use the "Problem-Action-Result" format. Use numbers if available.
        * **PARAGRAPH 3 (The Motivation / Why):** Explain *WHY* you want to join **{employer_name}** specifically. Connect your personal career goals or values to the company's mission/industry context found in the JD.
        * **PARAGRAPH 4 (Closing):** Reiterate enthusiasm and call to action (interview request).
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

# --- 5. MAIN UI LAYOUT ---

# Top Banner
st.markdown("""
<div class='top-banner'>
    <h1>⚡ Resume Matcher Pro</h1>
    <p>Advanced AI Analysis powered by Llama 3.1</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # --- QUICK START GUIDE ---
    with st.expander("🐣 Quick Start Guide", expanded=True):
        st.markdown("""
        **1. Upload:** Go to 'Upload Resume' tab.
        
        **2. Search:** Find jobs via Sidebar.
        
        **3. Analyze:** Click 'Deep Dive' for AI insights.
        
        **4. Apply:** Generate Cover Letter & Apply.
        """)
    
    st.markdown("---")
    st.markdown("## 🔍 Search Criteria")
    
    if st.session_state.resume_uploaded:
        st.success("✅ Resume Loaded")
    else:
        st.warning("📄 Upload Resume Required")
    
    st.markdown("---")
    
    st.markdown("### 💼 Job Details")
    job_title = st.text_input("Job Title", placeholder="e.g., Software Engineer")
    
    st.markdown("### 📍 Location Preferences")
    location = st.text_input("City, State, or 'Remote'", placeholder="e.g., New York, NY")
    
    st.markdown("---")
    
    if st.button("🚀 Search & Match Jobs", type="primary", disabled=not st.session_state.resume_uploaded):
        with st.spinner("Searching & Matching..."):
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
                    st.success(f"✅ Found {len(matches)} matches!")
                else:
                    st.session_state.matches_df = pd.DataFrame() 
                    st.error("❌ No jobs found. Try a broader search term.")
            except Exception as e:
                st.error(f"System Error: {str(e)}")
    
    if st.session_state.resume_uploaded:
        st.markdown("---")
        if st.button("🗑️ Clear Resume"):
            st.session_state.resume_text = ""
            st.session_state.resume_uploaded = False
            st.session_state.matches_df = pd.DataFrame()
            st.rerun()

# Logic to determine active tab
if not st.session_state.matches_df.empty:
    tab1, tab2 = st.tabs(["🎯 Matches", "📄 Upload"])
    matches_tab = tab1; upload_tab = tab2
else:
    tab1, tab2 = st.tabs(["📄 Upload", "🎯 Matches"])
    matches_tab = tab2; upload_tab = tab1

# --- UPLOAD TAB ---
with upload_tab:
    st.markdown("### 📤 Upload Resume")
    uploaded_file = st.file_uploader("PDF or DOCX", type=['pdf', 'docx'], label_visibility="collapsed")
    
    if uploaded_file and (st.session_state.last_uploaded_file != uploaded_file.name):
        with st.spinner("Parsing..."):
            try:
                if uploaded_file.name.endswith('.pdf'):
                    text = extract_text_from_pdf(uploaded_file)
                else:
                    text = extract_text_from_docx(uploaded_file)
                
                if text and len(clean_text(text)) > 50:
                    st.session_state.resume_text = clean_text(text)
                    st.session_state.resume_uploaded = True
                    st.session_state.last_uploaded_file = uploaded_file.name
                    st.success("✅ Uploaded!")
                    st.rerun()
                else:
                    st.error("❌ File empty or unreadable.")
            except Exception as e:
                st.error(f"Error: {e}")

# --- MATCHES TAB ---
with matches_tab:
    if st.session_state.matches_df.empty:
        st.info("Upload resume and search for jobs to see results.")
    else:
        for idx, row in st.session_state.matches_df.iterrows():
            score = row.get('match_score', 0)
            job_desc = row.get('job_description', '')
            job_title_txt = row.get('job_title', 'Job')
            employer = row.get('employer_name', 'Company')
            location_txt = row.get('location_display', 'Remote')
            job_id = row.get('job_id', f"job_{idx}")
            
            # --- RENDER JOB CARD ---
            st.markdown('<div class="job-card">', unsafe_allow_html=True)
            
            # 1. Header Row
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"<div class='job-title'>{job_title_txt}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='company-name'>🏢 {employer}</div>", unsafe_allow_html=True)
            
            with c2:
                s_class = "high-match" if score >= 75 else "med-match" if score >= 50 else "low-match"
                st.markdown(f"""
                <div class='score-badge {s_class}'>
                    <div class='score-val'>{score:.0f}%</div>
                    <div class='score-lbl'>Match</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)

            # 2. Meta Badges
            st.markdown(f"""
            <div class='meta-container'>
                <div class='meta-badge'>📍 {location_txt}</div>
                <div class='meta-badge'>💼 {row.get('job_employment_type', 'Full-time')}</div>
                <div class='meta-badge'>🏭 {row.get('industry', 'Tech')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 3. AI Insights Logic
            ai_data = st.session_state.ai_results.get(job_id)
            
            if ai_data:
                st.markdown('<div class="ai-insight-card">', unsafe_allow_html=True)
                
                if "⚠️" in ai_data.get('summary', ''):
                     st.markdown(f"<div class='summary-text' style='color:#fca5a5;'>{ai_data.get('summary')}</div>", unsafe_allow_html=True)
                else:
                    # Executive Summary
                    st.markdown(f"""
                    <div class='section-title'>📝 Executive Summary</div>
                    <div class='summary-text'>
                        {ai_data.get('summary')}
                        <br><br>
                        <em>🎯 <strong>Why this role?</strong> {ai_data.get('role_intent')}</em>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Tech Stack
                    tech = ai_data.get('tech_stack', [])
                    if tech:
                        st.markdown(f"<div class='section-title'>💻 Tech Stack</div>", unsafe_allow_html=True)
                        tech_html = "".join([f"<span class='tech-tag'>{t}</span>" for t in tech])
                        st.markdown(f"<div style='margin-bottom:2rem;'>{tech_html}</div>", unsafe_allow_html=True)

                    # Columns: Responsibilities vs Requirements
                    col_left, col_right = st.columns(2)
                    with col_left:
                        reqs = ai_data.get('key_responsibilities', [])
                        if reqs:
                            list_html = "".join([f"<li>{r}</li>" for r in reqs]) 
                            st.markdown(f"<div class='section-title'>📋 Responsibilities</div><ul class='clean-list'>{list_html}</ul>", unsafe_allow_html=True)
                    with col_right:
                        must_haves = ai_data.get('requirements', [])
                        if must_haves:
                            list_html = "".join([f"<li>{r}</li>" for r in must_haves]) 
                            st.markdown(f"<div class='section-title'>✅ Requirements</div><ul class='clean-list'>{list_html}</ul>", unsafe_allow_html=True)

                    # Education & Soft Skills
                    st.markdown("<br>", unsafe_allow_html=True)
                    c3, c4 = st.columns(2)
                    with c3:
                        ed = ai_data.get('education_cert', 'Not specified')
                        st.markdown(f"<div class='section-title'>🎓 Education</div><div style='color:var(--text-main); opacity:0.8;'>{ed}</div>", unsafe_allow_html=True)
                    with c4:
                        soft = ai_data.get('soft_skills', [])
                        if soft:
                            st.markdown(f"<div class='section-title'>🤝 Soft Skills</div>", unsafe_allow_html=True)
                            soft_html = "".join([f"<span class='soft-tag'>{s}</span>" for s in soft])
                            st.markdown(f"<div>{soft_html}</div>", unsafe_allow_html=True)

                    # Culture & Benefits Box
                    st.markdown(f"""
                    <div class='culture-box'>
                        <div class='section-title' style='color:#f97316; border-color:#f97316;'>🎁 Benefits & Culture</div>
                        <div style='display:grid; grid-template-columns: 1fr 1fr; gap:1rem; color:var(--text-main);'>
                            <div><strong>💰 Salary:</strong> {ai_data.get('salary_benefits', 'N/A')}</div>
                            <div><strong>🏠 Policy:</strong> {ai_data.get('remote_policy', 'N/A')}</div>
                        </div>
                        <div style='margin-top:1rem; opacity:0.8; font-style:italic;'>
                            "{ai_data.get('culture_vibe', 'Standard corporate culture.')}"
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
            else:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(f"✨ Deep Dive Analysis", key=f"ai_btn_{idx}", use_container_width=True):
                    if GROQ_ENABLED:
                        with st.spinner("🤖 Deep diving into job details..."):
                            result = get_ai_analysis(job_desc, job_title_txt, employer)
                            if result:
                                st.session_state.ai_results[job_id] = result
                                st.rerun()
                            else:
                                st.error("Analysis Failed")
                    else:
                        st.warning("⚠️ Add GROQ_API_KEY to .env")

            # --- COVER LETTER SECTION ---
            cl_text = st.session_state.cover_letters.get(job_id)
            if cl_text:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### 📝 Draft Cover Letter")
                tab_preview, tab_edit = st.tabs(["📄 Preview Paper", "✏️ Edit Text"])
                
                with tab_preview:
                    st.markdown(f"<div class='paper-doc'><div class='paper-header'>DRAFT DOCUMENT</div>{cl_text}</div>", unsafe_allow_html=True)
                
                with tab_edit:
                    edited_cl = st.text_area("Edit:", value=cl_text, height=400, key=f"edit_cl_{idx}")
                    if st.button("💾 Save Edits", key=f"save_cl_{idx}"):
                        st.session_state.cover_letters[job_id] = edited_cl
                        st.rerun()

                st.download_button("📥 Download Text", st.session_state.cover_letters[job_id], f"Cover_Letter_{employer}.txt", use_container_width=True, key=f"dl_cl_{idx}")
            
            # Footer Buttons
            st.markdown("<div style='margin-top: 2rem;'>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns([1, 1])
            with col_b1:
                lbl = "⚡ Regenerate Letter" if cl_text else "✍️ Draft Cover Letter"
                if st.button(lbl, key=f"cl_btn_{idx}", use_container_width=True):
                    if GROQ_ENABLED:
                         with st.spinner("✍️ Writing evidence-based letter..."):
                            letter = generate_cover_letter(st.session_state.resume_text, job_desc, job_title_txt, employer)
                            st.session_state.cover_letters[job_id] = letter
                            st.rerun()
                    else:
                         st.warning("⚠️ Enable AI to use this.")
            with col_b2:
                if row.get('job_apply_link'):
                    st.link_button("🚀 Apply For This Role", row['job_apply_link'], use_container_width=True)
            
            st.markdown("</div></div>", unsafe_allow_html=True) # End Job Card

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; opacity: 0.7;'>Resume Matcher • Powered by Groq Llama 3.1</div>", unsafe_allow_html=True)