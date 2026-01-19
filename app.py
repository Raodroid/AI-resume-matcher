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
from datetime import datetime
import streamlit.components.v1 as components

# --- 1. CONFIGURATION & SETUP ---

load_dotenv()

# --- DATABASE & TRACKING LOGIC ---
HISTORY_FILE = "job_tracker.csv"

def load_history():
    try:
        df = pd.read_csv(HISTORY_FILE)
    except FileNotFoundError:
        # Added "Link" column
        df = pd.DataFrame(columns=["Date", "Company", "Role", "Status", "Link", "Match Score"])
        df.to_csv(HISTORY_FILE, index=False)
    return df

## --- TRACKER DIALOG (CLEAN VERSION) ---
@st.dialog("📋 Application Tracker", width="large")
def open_tracker_dialog():
    st.caption("Manage your job search pipeline here. Changes save automatically.")
    
    df = load_history()
    
    if not df.empty:
        # 1. Force Text Types (Prevents "Float" Error)
        df["Role"] = df["Role"].fillna("").astype(str)
        df["Company"] = df["Company"].fillna("").astype(str)
        df["Link"] = df["Link"].fillna("").astype(str)
        
        # 2. FILTER COLUMNS: Remove Match Score/Notes
        # We explicitly select only the columns we want to display.
        # Note: Saving this will remove the hidden columns from your CSV file.
        target_columns = ["Status", "Link", "Date", "Role", "Company"]
        
        # Safety: Ensure columns exist before selecting
        for col in target_columns:
            if col not in df.columns:
                df[col] = ""
                
        # Apply the filter
        df = df[target_columns]

        # 3. FULL WIDTH EDITOR
        edited_df = st.data_editor(
            df,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    width="medium",
                    options=["👀 Interested", "📨 Applied", "🗣️ Interview", "✅ Offer", "❌ Rejected"],
                    required=True,
                ),
                "Link": st.column_config.LinkColumn("Link", display_text="Open Job"),
                "Date": st.column_config.TextColumn("Date", disabled=True),
                "Role": st.column_config.TextColumn("Role", width="medium"),
                "Company": st.column_config.TextColumn("Company", width="medium"),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic", # Allows deleting rows
            key="dialog_editor"
        )
        
        if not edited_df.equals(df):
            update_history(edited_df)
            st.rerun()
    else:
        st.info("No jobs tracked yet. Click 'Apply' on a job card to start!")
def save_click(company, role, link, score):
    """Auto-saves when user clicks Apply."""
    df = load_history()
    
    # Avoid duplicates: Check if Company + Role already exists
    if not ((df['Company'] == company) & (df['Role'] == role)).any():
        new_entry = {
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Company": company,
            "Role": role,
            "Status": "👀 Interested", # Default status when clicking apply
            "Link": link,
        }
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv(HISTORY_FILE, index=False)

def update_history(df):
    df.to_csv(HISTORY_FILE, index=False)

st.set_page_config(
    page_title="HirePilot.Ai",
    page_icon="🚀",
    layout="wide",
    menu_items={
        'Report a bug': 'https://github.com/Raodroid/issues',
        'About': """
        # 🚀 HirePilot.Ai
        
        **The AI-Powered Job Search Assistant**
        
        > *"Stop searching, start landing."*
        
        ---
        
        **Version:** 1.2.0  
        **Built with:** Python, Streamlit & Groq LPU  
        
        Made with AI for job searchers.
        """
    }
)

# --- 2. LOAD CSS ---
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"⚠️ Could not find {file_name}. Make sure it is in the same folder.")

local_css("style.css")

def get_groq_key():
    # Priority 1: System Environment Variable (Local .env)
    key = os.getenv("GROQ_API_KEY")
    
    # Priority 2: Streamlit Secrets (Cloud Deployment)
    if not key:
        try:
            key = st.secrets["GROQ_API_KEY"]
        except:
            pass
            
    return key

# 3. Retrieve and Sanitize
raw_api_key = get_groq_key()
GROQ_ENABLED = False

if raw_api_key:
    try:
        # --- THE FIX FOR 401 ERRORS ---
        # .strip() removes accidental spaces at start/end
        # .replace() removes accidental quotes if you pasted them in the config
        clean_key = raw_api_key.strip().replace('"', '').replace("'", "")
        
        client = Groq(api_key=clean_key)
        GROQ_ENABLED = True
        
        # Optional: verify it works (uncomment to test)
        # client.models.list() 
        
    except Exception as e:
        st.error(f"⚠️ Groq Init Error: {e}")
else:
    st.warning("⚠️ GROQ_API_KEY not found. Please check your .env or Secrets.")

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
            max_tokens=3000,
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
        * **SIGN-OFF:** End with "Yours Sincerely," followed by a newline and the [Candidate Name].
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
    <h1>HirePilot.ai</h1>
    <div class="typing-subtitle-wrapper">
        <p class="typing-subtitle">Automate your job search today.</p>
    </div>
</div>""", unsafe_allow_html=True)


# --- STEP 1: UPLOAD RESUME ---
st.markdown('<div id="step-1-header" class="step-header" data-step="1"><div class="step-number">1</div> Upload Your Resume</div>', unsafe_allow_html=True)
st.markdown('<div id="step-1-content" class="step-content" data-step="1">', unsafe_allow_html=True)

if not st.session_state.resume_uploaded:
    uploaded_file = st.file_uploader("Upload PDF or DOCX", type=['pdf', 'docx'], label_visibility="collapsed")

    if uploaded_file and (st.session_state.last_uploaded_file != uploaded_file.name):
        progress_text = "Analyzing Profile..."
        my_bar = st.progress(0, text=progress_text)
        
        # Add custom progress bar styling
        st.markdown("""
        <style>
        .stProgress > div > div > div {
            background: linear-gradient(90deg, #3b82f6 0%, #06b6d4 50%, #3b82f6 100%);
            background-size: 200% 100%;
            animation: progress-fill 1s ease-out forwards, gradient-move 2s ease infinite;
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.4);
        }
        </style>
        """, unsafe_allow_html=True)
    
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
    st.markdown('<div data-step-complete="1" style="display:none;"></div>', unsafe_allow_html=True)
    with st.expander("Resume is loaded and ready for matching.", expanded=True):
        if st.button("Upload Different Resume"):
            st.session_state.resume_uploaded = False
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- STEP 2: SEARCH JOBS ---
if st.session_state.resume_uploaded:
    st.markdown("---")
    st.markdown('<div id="step-2-header" class="step-header" data-step="2"><div class="step-number">2</div> Find Your Dream Job</div>', unsafe_allow_html=True)
    st.markdown('<div id="step-2-content" class="step-content" data-step="2">', unsafe_allow_html=True)
    
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
                st.markdown('<div data-step-complete="2" style="display:none;"></div>', unsafe_allow_html=True)
                st.rerun()
            else:
                st.session_state.matches_df = pd.DataFrame() 
                st.error("❌ No jobs found. Try a broader search term.")
        except Exception as e:
            st.error(f"System Error: {str(e)}")
    st.markdown('</div>', unsafe_allow_html=True)

# --- STEP 3: MATCHED RESULTS ---
if not st.session_state.matches_df.empty:
    st.markdown("---")
    st.markdown('<div id="step-3-header" class="step-header" data-step="3"><div class="step-number">3</div> Matched Roles</div>', unsafe_allow_html=True)
    st.markdown('<div data-step-complete="3" style="display:none;"></div>', unsafe_allow_html=True)
    
    st.success(f"Found {len(st.session_state.matches_df)} jobs matching your resume!")

    for idx, row in st.session_state.matches_df.iterrows():
        score = row.get('match_score', 0)
        job_desc = row.get('job_description', '')
        job_title_txt = row.get('job_title', 'Job')
        employer = row.get('employer_name', 'Company')
        location_txt = row.get('location_display', 'Remote')
        job_id = row.get('job_id', f"job_{idx}")
        
        # --- RENDER JOB CARD ---
        st.markdown('<div class="job-card">', unsafe_allow_html=True)
        
        # 1. Header Row - Compact Layout
        st.markdown('<div class="job-card-header">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)

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
                    st.markdown(f"<div style='margin-bottom:1rem;'>{tech_html}</div>", unsafe_allow_html=True)

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

                # Culture & Benefits Box - Integrated into AI Analysis
                st.markdown(f"""
                <div class='culture-box'>
                    <div class='section-title' style='color:#3b82f6; border-color:#3b82f6; margin-top:0.75rem;'>🎁 Benefits & Culture</div>
                    <div style='display:grid; grid-template-columns: 1fr 1fr; gap:0.75rem; color:var(--text-main); margin-top:0.5rem;'>
                        <div><strong>💰 Salary:</strong> {ai_data.get('salary_benefits', 'N/A')}</div>
                        <div><strong>🏠 Policy:</strong> {ai_data.get('remote_policy', 'N/A')}</div>
                    </div>
                    <div style='margin-top:0.75rem; opacity:0.8; font-style:italic; font-size:0.95rem;'>
                        "{ai_data.get('culture_vibe', 'Standard corporate culture.')}"
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
        else:
            # Deep Dive Button - Clean, no wrapper divs
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
            st.markdown('<div class="step-content" style="margin-top:1.5rem;">', unsafe_allow_html=True)
            st.markdown("### 📝 Draft Cover Letter")
            tab_preview, tab_edit = st.tabs(["📄 Preview Paper", "✏️ Edit Text"])
            
            with tab_preview:
                st.markdown(f"<div class='paper-doc'><div class='paper-header'>DRAFT COVER LETTER</div>{cl_text}</div>", unsafe_allow_html=True)
            
            with tab_edit:
                edited_cl = st.text_area("Edit:", value=cl_text, height=400, key=f"edit_cl_{idx}")
                if st.button("💾 Save Edits", key=f"save_cl_{idx}"):
                    st.session_state.cover_letters[job_id] = edited_cl
                    st.rerun()

            st.download_button("📥 Download Text", st.session_state.cover_letters[job_id], f"Cover_Letter_{employer}.txt", use_container_width=True, key=f"dl_cl_{idx}")
            st.markdown('</div>', unsafe_allow_html=True)
        
# Footer Buttons - Compact
        st.markdown("<div style='margin-top: 1.5rem;'>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns([1, 1])
        
        # --- BUTTON 1: COVER LETTER (Existing) ---
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
        
# --- BUTTON 2: SMART APPLY (Reliable Track-then-Go Pattern) ---
        with col_b2:
            target_link = row.get('job_apply_link') or row.get('job_url') or '#'
            
            # 1. Check if link exists
            if target_link and target_link != '#':
                
                # Unique keys for state management
                track_key = f"track_state_{job_id}_{idx}"
                
                # 2. Check State: Has the user clicked "Track" yet?
                if st.session_state.get(track_key, False):
                    # STATE B: User tracked it -> Show the Link Button
                    # This is a native link button, so it ALWAYS works.
                    st.link_button(
                        "🔗 Go to Site ➡", 
                        url=target_link, 
                        type="primary", 
                        use_container_width=True
                    )
                else:
                    # STATE A: User hasn't clicked yet -> Show "Apply & Track"
                    if st.button("🚀 Apply & Track", key=f"btn_track_{idx}", use_container_width=True):
                        # B. Update State to show the link button next
                        st.session_state[track_key] = True
                        # A. Save to Tracker
                        current_score = ai_data.get('compatibility_score', 'N/A') if ai_data else 'N/A'
                        save_click(employer, job_title_txt, target_link, current_score)
                        
                        # C. Toast and Rerun to swap the buttons instantly
                        st.toast(f"Saved! Click the link to open.", icon="✅")
                        st.rerun()
            else:
                st.button("🚫 Link Not Available", disabled=True, key=f"no_link_{idx}", use_container_width=True)

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; opacity: 0.7;'> HirePilot.Ai • Powered by Groq Llama 3.1</div>", unsafe_allow_html=True)

# --- SIDEBAR: CLEAN DASHBOARD WIDGET ---
with st.sidebar:
    st.markdown("---")
    
    # 1. Load Data
    df_history = load_history()
    
    # 2. Check if data exists
    if not df_history.empty:
        # Calculate Stats
        count_interested = len(df_history[df_history['Status'] == "👀 Interested"])
        count_applied = len(df_history[df_history['Status'] == "📨 Applied"])
        count_interview = len(df_history[df_history['Status'] == "🗣️ Interview"])
        
        # Determine badge color dynamically
        review_badge_class = 'urgent-badge' if count_interested > 0 else 'stat-badge-mini'
        
        # 3. CSS Styles (No Indentation!)
        st.markdown("""
<style>
.tracker-card {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 15px;
}
.tracker-title {
    font-size: 0.85rem;
    font-weight: 700;
    color: #94a3b8;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    padding-bottom: 8px;
}
.stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-size: 0.9rem;
    color: #e2e8f0;
}
.stat-badge-mini {
    background: rgba(59, 130, 246, 0.2);
    color: #60a5fa;
    padding: 2px 8px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.8rem;
}
.urgent-badge {
    background: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
    padding: 2px 8px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.8rem;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.6; }
    100% { opacity: 1; }
}
</style>
""", unsafe_allow_html=True)

        # 4. Render HTML Widget (No Indentation!)
        html_content = f"""
<div class="tracker-card">
    <div class="tracker-title">🚦 Pipeline Status</div>
    <div class="stat-row">
        <span>👀 To Review</span>
        <span class="{review_badge_class}">{count_interested}</span>
    </div>
    <div class="stat-row">
        <span>📨 Applied</span>
        <span class="stat-badge-mini">{count_applied}</span>
    </div>
    <div class="stat-row">
        <span>🗣️ Interview</span>
        <span class="stat-badge-mini">{count_interview}</span>
    </div>
</div>
"""
        st.markdown(html_content, unsafe_allow_html=True)
        
        # 5. The Action Button
        if st.button("📂 Open Full Tracker", use_container_width=True):
            open_tracker_dialog()
            
    else:
        st.info("Your tracker is empty.")
        st.caption("Click 'Apply' on a job to auto-track it here.")