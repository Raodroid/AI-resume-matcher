import streamlit as st
import pandas as pd
import os
import json
import re
from dotenv import load_dotenv
from groq import Groq

# --- 1. CONFIGURATION & SETUP ---

# Load environment variables FIRST
load_dotenv()

# Set page config
st.set_page_config(
    page_title="Resume Matcher Pro",
    page_icon="🤖",
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

# --- 2. CSS STYLING (ENHANCED UI) ---
st.markdown("""
<style>
    /* Main background */
    .stApp { 
        background-color: #0f172a;
        color: #f1f5f9;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] { 
        background-color: #1e293b; 
        border-right: 1px solid #334155; 
    }
    
    /* Job Card Container - MAXIMUM SIZE */
    .job-card {
        background: #1e293b;
        border-radius: 24px;
        padding: 3rem;
        margin: 2.5rem 0;
        border: 1px solid #334155;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    .job-card:hover {
        border-color: #3b82f6;
    }

    /* AI Insight Section */
    .ai-insight-card {
        background: rgba(15, 23, 42, 0.6); 
        border-radius: 16px;
        padding: 2rem;
        margin-top: 2rem;
        border: 1px solid #334155;
        animation: fadeIn 0.5s;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    /* Section Headers */
    .section-title {
        color: #f97316; 
        font-size: 1.1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 800;
        margin-bottom: 1.2rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        border-bottom: 2px solid rgba(249, 115, 22, 0.2);
        padding-bottom: 0.5rem;
    }

    /* Summary Text */
    .summary-text {
        font-size: 1.1rem;
        line-height: 1.8;
        color: #e2e8f0;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    /* Clean Bullet List */
    ul.clean-list {
        list-style-type: none; 
        padding: 0;
        margin: 0;
    }

    ul.clean-list li {
        position: relative;
        padding-left: 2rem;
        margin-bottom: 1rem;
        color: #cbd5e1;
        font-size: 1rem;
        line-height: 1.6;
    }

    ul.clean-list li::before {
        content: "🔹"; 
        position: absolute;
        left: 0;
        font-size: 0.9rem;
        color: #60a5fa;
    }

    /* Tech Stack Badges (Code Style) */
    .tech-tag {
        display: inline-block;
        background: #0f172a;
        color: #60a5fa;
        border: 1px solid #1e40af;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        font-weight: 700;
        margin: 0 0.5rem 0.5rem 0;
    }

    /* Soft Skill Badges (Pill Style) */
    .soft-tag {
        display: inline-block;
        background: rgba(16, 185, 129, 0.1);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 0.4rem 1rem;
        border-radius: 99px;
        font-size: 0.9rem;
        margin: 0 0.5rem 0.5rem 0;
    }

    /* Culture/Benefits Box */
    .culture-box {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(30, 58, 138, 0.1) 100%);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1.5rem;
    }

    /* Score Badge - Giant */
    .score-badge {
        background: rgba(15, 23, 42, 0.8);
        border: 2px solid #334155;
        border-radius: 20px;
        padding: 1.5rem;
        text-align: center;
        min-width: 120px;
    }
    .score-val { font-size: 2.8rem; font-weight: 900; line-height: 1; margin-bottom: 0.2rem; }
    .score-lbl { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.1em; color: #94a3b8; }
    
    .high-match { color: #34d399; border-color: #34d399; }
    .med-match { color: #fbbf24; border-color: #fbbf24; }
    .low-match { color: #f87171; border-color: #f87171; }

    /* Meta Badges UI */
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
        border: 1px solid;
    }
    
    .meta-location { background: rgba(59, 130, 246, 0.1); color: #93c5fd; border-color: rgba(59, 130, 246, 0.3); }
    .meta-type { background: rgba(168, 85, 247, 0.1); color: #d8b4fe; border-color: rgba(168, 85, 247, 0.3); }
    .meta-industry { background: rgba(20, 184, 166, 0.1); color: #5eead4; border-color: rgba(20, 184, 166, 0.3); }

    /* Apply Button - Massive */
    .stLinkButton > a {
        background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%) !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 1rem 2rem !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        text-align: center !important;
        text-decoration: none !important;
        display: block !important;
        border: none !important;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.4) !important;
        transition: transform 0.2s !important;
    }
    .stLinkButton > a:hover {
        transform: translateY(-2px) !important;
        background: linear-gradient(90deg, #1d4ed8 0%, #2563eb 100%) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. GROQ AI HELPER FUNCTION (SUPER-COMPREHENSIVE) ---

@st.cache_data(show_spinner=False, ttl=3600)
def get_ai_analysis(job_description, job_title, employer_name):
    """
    Uses Groq (Llama 3.1) to extract comprehensive job details.
    """
    if not GROQ_ENABLED:
        return {"summary": "⚠️ API Key missing. Add GROQ_API_KEY to .env file."}
    
    desc_text = str(job_description).strip()
    if len(desc_text) < 50:
        return {"summary": "⚠️ Description too short for analysis."}
    
    # Clean text
    desc_text = desc_text.replace("{", "(").replace("}", ")").replace('"', "'")
    
    try:
        system_prompt = "You are a Senior Technical Recruiter. Analyze job descriptions deeply."
        
        user_prompt = f"""
        Analyze this job posting for "{job_title}" at "{employer_name}".
        
        Return a valid JSON object (AND NOTHING ELSE) with these specific keys:
        {{
            "summary": "A rich 3-4 sentence executive summary describing the role's core mission.",
            "role_intent": "One sentence explaining WHY they are hiring (e.g. 'To scale their cloud infra' or 'Backfill a lead role').",
            "tech_stack": ["List specific tools, languages, frameworks mentioned (e.g. Python, AWS, React)"],
            "soft_skills": ["List key personality traits/soft skills (e.g. Leadership, Communication)"],
            "key_responsibilities": ["List of 4-5 specific daily duties"],
            "requirements": ["List of 4-5 must-have qualifications"],
            "education_cert": "Education or Certifications required (e.g. BSCS, AWS Certified)",
            "remote_policy": "Specifics on remote/hybrid/onsite policy",
            "salary_benefits": "Salary range and key perks (e.g. $120k, 401k, Unlimited PTO)",
            "culture_vibe": "Brief description of the team culture or company mission"
        }}
        
        Job Description:
        {desc_text[:15000]} 
        """
        
        # Call API - using llama-3.1-8b-instant
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        
        response_text = completion.choices[0].message.content
        
        # Robust Parsing Logic
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx : end_idx + 1]
                return json.loads(json_str)
            else:
                return {"summary": "⚠️ AI output format error (No JSON found)."}
        except json.JSONDecodeError:
            return {"summary": "⚠️ AI JSON parsing failed."}
            
    except Exception as e:
        error_details = str(e)
        if hasattr(e, 'response') and e.response:
            error_details = f"{e.response.status_code} - {e.response.text}"
        return {"summary": f"⚠️ Groq Error: {error_details[:200]}"}

# --- 4. APP STATE ---
if 'resume_text' not in st.session_state: st.session_state.resume_text = ""
if 'jobs_df' not in st.session_state: st.session_state.jobs_df = pd.DataFrame()
if 'matches_df' not in st.session_state: st.session_state.matches_df = pd.DataFrame()
if 'resume_uploaded' not in st.session_state: st.session_state.resume_uploaded = False
if 'last_uploaded_file' not in st.session_state: st.session_state.last_uploaded_file = None
if 'ai_results' not in st.session_state: st.session_state.ai_results = {} 

# --- 5. MAIN UI LAYOUT ---

st.markdown("""
<div style='text-align: center; padding: 4rem 0; background: linear-gradient(135deg, #ea580c 0%, #f97316 50%, #fbbf24 100%); border-radius: 0 0 40px 40px; margin-bottom: 3rem; box-shadow: 0 20px 40px -10px rgba(249, 115, 22, 0.4);'>
    <h1 style='color: white; margin: 0; font-size: 4rem; text-shadow: 0 4px 8px rgba(0,0,0,0.2); letter-spacing: -1px;'>⚡ Resume Matcher Pro</h1>
    <p style='color: rgba(255,255,255,0.95); margin-top: 1rem; font-size: 1.4rem; font-weight: 500;'>Advanced AI Analysis powered by Llama 3.1</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 🔍 Search Criteria")
    
    if st.session_state.resume_uploaded:
        st.success("✅ Resume Loaded")
    else:
        st.warning("📄 Upload Resume Required")
    
    st.markdown("---")
    
    st.markdown("### 💼 Job Details")
    job_title = st.text_input("Job Title", placeholder="e.g., Software Engineer")
    
    st.markdown("### 📍 Location Preferences")
    location = st.text_input("City, State, or 'Remote'", placeholder="e.g., Singapore")
    
    st.markdown("---")
    
    if st.button("🚀 Search & Match Jobs", type="primary", disabled=not st.session_state.resume_uploaded):
        with st.spinner("Searching & Matching..."):
            try:
                api = JobSearchAPI()
                jobs = api.search_jobs(query=job_title, location=location, num_pages=1)
                
                if not jobs.empty:
                    st.session_state.jobs_df = jobs
                    st.session_state.ai_results = {} 
                    
                    matcher = JobMatcher()
                    matches = matcher.match_resume_to_jobs(
                        st.session_state.resume_text,
                        st.session_state.jobs_df,
                        top_n=10
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
            job_title = row.get('job_title', 'Job')
            employer = row.get('employer_name', 'Company')
            location_txt = row.get('location_display', 'Remote')
            job_id = row.get('job_id', f"job_{idx}")
            
            # --- RENDER JOB CARD ---
            st.markdown('<div class="job-card">', unsafe_allow_html=True)
            
            # 1. Header Row
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"<h1 style='color:#f8fafc; margin:0; font-size:2rem; font-weight:800;'>{job_title}</h1>", unsafe_allow_html=True)
                st.markdown(f"<div style='color:#94a3b8; font-size:1.4rem; margin-top:0.5rem; font-weight:500;'>🏢 {employer}</div>", unsafe_allow_html=True)
            
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
            j_type = row.get('job_employment_type', 'Full-time')
            j_ind = row.get('industry', 'Technology')
            
            st.markdown(f"""
            <div class='meta-container'>
                <div class='meta-badge meta-location'>📍 {location_txt}</div>
                <div class='meta-badge meta-type'>💼 {j_type}</div>
                <div class='meta-badge meta-industry'>🏭 {j_ind}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 3. AI Insights Logic (ON DEMAND)
            ai_data = st.session_state.ai_results.get(job_id)
            
            if ai_data:
                # --- RENDER AI RESULTS ---
                st.markdown('<div class="ai-insight-card">', unsafe_allow_html=True)
                
                if "⚠️" in ai_data.get('summary', ''):
                     st.markdown(f"<div class='summary-text' style='color:#fca5a5;'>{ai_data.get('summary')}</div>", unsafe_allow_html=True)
                else:
                    # Executive Summary & Role Intent
                    st.markdown(f"""
                    <div class='section-title'>📝 Executive Summary</div>
                    <div class='summary-text'>
                        {ai_data.get('summary')}
                        <br><br>
                        <em>🎯 <strong>Why this role?</strong> {ai_data.get('role_intent')}</em>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Tech Stack (Code Badges)
                    tech = ai_data.get('tech_stack', [])
                    if tech:
                        st.markdown(f"<div class='section-title'>💻 Tech Stack</div>", unsafe_allow_html=True)
                        tech_html = "".join([f"<span class='tech-tag'>{t}</span>" for t in tech])
                        st.markdown(f"<div style='margin-bottom:2rem;'>{tech_html}</div>", unsafe_allow_html=True)

                    # Two Columns: Responsibilities vs Requirements
                    col_left, col_right = st.columns(2)
                    
                    with col_left:
                        reqs = ai_data.get('key_responsibilities', [])
                        if reqs:
                            list_html = "".join([f"<li>{r}</li>" for r in reqs]) 
                            st.markdown(f"""
                            <div class='section-title'>📋 Key Responsibilities</div>
                            <ul class='clean-list'>{list_html}</ul>
                            """, unsafe_allow_html=True)
                    
                    with col_right:
                        must_haves = ai_data.get('requirements', [])
                        if must_haves:
                            list_html = "".join([f"<li>{r}</li>" for r in must_haves]) 
                            st.markdown(f"""
                            <div class='section-title'>✅ Must-Have Requirements</div>
                            <ul class='clean-list'>{list_html}</ul>
                            """, unsafe_allow_html=True)

                    # Education & Soft Skills Row
                    st.markdown("<br>", unsafe_allow_html=True)
                    c3, c4 = st.columns(2)
                    with c3:
                        ed = ai_data.get('education_cert', 'Not specified')
                        st.markdown(f"<div class='section-title'>🎓 Education & Certs</div><div style='color:#cbd5e1;'>{ed}</div>", unsafe_allow_html=True)
                    with c4:
                        soft = ai_data.get('soft_skills', [])
                        if soft:
                            st.markdown(f"<div class='section-title'>🤝 Soft Skills</div>", unsafe_allow_html=True)
                            soft_html = "".join([f"<span class='soft-tag'>{s}</span>" for s in soft])
                            st.markdown(f"<div>{soft_html}</div>", unsafe_allow_html=True)

                    # Culture & Benefits Box
                    st.markdown(f"""
                    <div class='culture-box'>
                        <div class='section-title' style='color:#60a5fa; border-color:#60a5fa;'>🎁 Compensation, Benefits & Culture</div>
                        <div style='display:grid; grid-template-columns: 1fr 1fr; gap:1rem; color:#e2e8f0;'>
                            <div><strong>💰 Salary:</strong> {ai_data.get('salary_benefits', 'Not specified')}</div>
                            <div><strong>🏠 Remote Policy:</strong> {ai_data.get('remote_policy', 'Not specified')}</div>
                        </div>
                        <div style='margin-top:1rem; color:#94a3b8; font-style:italic;'>
                            "{ai_data.get('culture_vibe', 'Standard corporate culture.')}"
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
                
            else:
                # --- RENDER ANALYZE BUTTON ---
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(f"✨ Analyze with AI (Deep Dive)", key=f"ai_btn_{idx}", use_container_width=True):
                    if GROQ_ENABLED:
                        with st.spinner("🤖 Deep diving into job details..."):
                            result = get_ai_analysis(job_desc, job_title, employer)
                            if result:
                                st.session_state.ai_results[job_id] = result
                                st.rerun()
                            else:
                                st.error("Analysis Failed")
                    else:
                        st.warning("⚠️ Add GROQ_API_KEY to .env to use this feature.")

            # 4. Action Buttons (Footer)
            st.markdown("<div style='margin-top: 2.5rem;'>", unsafe_allow_html=True)
            if row.get('job_apply_link'):
                st.link_button("🚀 Apply For This Role", row['job_apply_link'], use_container_width=True)
            
            st.markdown("</div>", unsafe_allow_html=True) 
            st.markdown("</div>", unsafe_allow_html=True) # End Job Card

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #6b7280;'>Resume Matcher • Powered by Groq Llama 3.1</div>", unsafe_allow_html=True)