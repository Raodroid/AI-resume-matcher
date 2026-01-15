import streamlit as st
import pandas as pd
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

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

# Configure Google Gemini
api_key = os.getenv("GOOGLE_API_KEY")
GEMINI_ENABLED = False

if api_key:
    try:
        genai.configure(api_key=api_key)
        GEMINI_ENABLED = True
    except Exception as e:
        st.error(f"⚠️ Gemini configuration error: {e}")
else:
    st.warning("⚠️ GOOGLE_API_KEY not found in .env file")

# Import our modules
try:
    from job_api import JobSearchAPI
    from job_matcher_simple import JobMatcher
    from resume_parser_simple import extract_text_from_pdf, extract_text_from_docx, clean_text
except ImportError as e:
    st.error(f"❌ Failed to import modules: {e}")
    st.stop()

# --- 2. CSS STYLING ---
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
    
    /* Job Card Container */
    .job-card {
        background: #1e293b;
        border-radius: 16px;
        padding: 2rem;
        margin: 1.5rem 0;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s;
    }
    .job-card:hover {
        border-color: #3b82f6;
        transform: translateY(-2px);
    }

    /* AI Insight Section */
    .ai-insight-card {
        margin-top: 1.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid #334155;
        animation: fadeIn 0.5s;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    /* Section Headers */
    .section-title {
        color: #60a5fa;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 700;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Summary Text - Clean & Readable */
    .summary-text {
        font-size: 1rem;
        line-height: 1.6;
        color: #e2e8f0;
        margin-bottom: 1.5rem;
        padding-left: 1rem;
        border-left: 3px solid #3b82f6; /* Blue accent line */
    }

    /* Clean Bullet List */
    ul.clean-list {
        list-style-type: none; 
        padding: 0;
        margin: 0 0 1.5rem 0;
    }

    ul.clean-list li {
        position: relative;
        padding-left: 1.5rem;
        margin-bottom: 0.6rem;
        color: #cbd5e1;
        font-size: 0.95rem;
        line-height: 1.5;
    }

    /* Custom Bullet Point (Arrow) */
    ul.clean-list li::before {
        content: "→"; 
        position: absolute;
        left: 0;
        color: #60a5fa;
        font-weight: bold;
    }

    /* Skill Tags - Modern Pill Shape */
    .modern-tag {
        display: inline-block;
        background: rgba(30, 41, 59, 1);
        color: #93c5fd;
        border: 1px solid #334155;
        padding: 0.35rem 0.8rem;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 500;
        margin: 0 0.4rem 0.4rem 0;
        transition: all 0.2s;
    }
    .modern-tag:hover {
        border-color: #60a5fa;
        background: rgba(59, 130, 246, 0.1);
    }

    /* Score Badge */
    .score-badge {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 0.8rem;
        text-align: center;
        min-width: 80px;
    }
    .score-val { font-size: 1.8rem; font-weight: 800; line-height: 1; }
    .score-lbl { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.2rem; }
    
    .high-match { color: #34d399; border-color: rgba(52, 211, 153, 0.3); }
    .med-match { color: #fbbf24; border-color: rgba(251, 191, 36, 0.3); }
    .low-match { color: #f87171; border-color: rgba(248, 113, 113, 0.3); }

    /* Basic Info Grid */
    .meta-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 1rem;
        margin-bottom: 1rem;
    }
    .meta-item {
        background: rgba(255,255,255,0.03);
        padding: 0.6rem;
        border-radius: 8px;
        font-size: 0.85rem;
        color: #94a3b8;
    }
    .meta-item strong { color: #f1f5f9; display: block; margin-bottom: 0.2rem; }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        transition: all 0.2s;
    }
    
    /* Preview Box */
    .preview-box {
        background: #1e293b; padding: 1.5rem; border-radius: 12px; border: 1px solid #475569;
        font-family: monospace; white-space: pre-wrap; max-height: 500px; overflow-y: auto; color: #cbd5e1;
    }
    
    /* Job Description Box */
    .job-description-box {
        color: #cbd5e1; font-size: 0.95rem; line-height: 1.8; padding: 1.5rem;
        background: #0f172a; border-radius: 12px; margin-top: 1.5rem; border: 1px solid #334155;
        white-space: pre-line;
    }
    
    /* Loading Animation */
    .loading-spinner {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
        color: #60a5fa;
    }
    
    /* Success Message */
    .success-message {
        color: #34d399;
        background: rgba(52, 211, 153, 0.1);
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 4px solid #34d399;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. SIMPLIFIED AI HELPER FUNCTION ---

@st.cache_data(show_spinner=False, ttl=3600)
def analyze_job_with_gemini(job_description, job_title, employer_name):
    """
    Simple function to get AI summary of job description and requirements
    """
    if not GEMINI_ENABLED:
        return {
            "summary": "⚠️ Google Gemini AI is not enabled. Please add GOOGLE_API_KEY to your .env file.",
            "requirements": []
        }
    
    if not job_description or len(str(job_description).strip()) < 50:
        return {
            "summary": "⚠️ Job description is too short for analysis.",
            "requirements": []
        }
    
    try:
        # Use the simplest model that works
        # Try gemini-1.5-flash if gemini-2.0-flash doesn't work
        model = genai.GenerativeModel('gemini-pro')  # Most reliable model
        
        prompt = f"""
        Please analyze this job posting and provide:
        1. A brief 2-3 sentence summary of what this job is about
        2. The main requirements/skills needed
        
        Job Title: {job_title}
        Company: {employer_name}
        
        Job Description:
        {str(job_description)[:4000]}
        
        Return your response in this exact JSON format:
        {{
            "summary": "Your 2-3 sentence summary here",
            "requirements": ["Requirement 1", "Requirement 2", "Requirement 3", "Requirement 4", "Requirement 5"]
        }}
        """
        
        response = model.generate_content(prompt)
        
        # Clean and parse the response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Parse JSON
        try:
            result = json.loads(response_text)
            # Ensure required fields exist
            if "summary" not in result:
                result["summary"] = "Summary not provided."
            if "requirements" not in result:
                result["requirements"] = []
            return result
        except json.JSONDecodeError:
            # If JSON parsing fails, create a simple response from the text
            return {
                "summary": response_text[:300] + ("..." if len(response_text) > 300 else ""),
                "requirements": ["AI analysis completed successfully"]
            }
            
    except Exception as e:
        error_msg = str(e)
        # Provide helpful error messages
        if "API key not valid" in error_msg or "403" in error_msg:
            return {
                "summary": "⚠️ Invalid Google API Key. Please check your .env file.",
                "requirements": []
            }
        elif "429" in error_msg:
            return {
                "summary": "⚠️ API rate limit exceeded. Please wait a minute and try again.",
                "requirements": []
            }
        elif "404" in error_msg:
            return {
                "summary": "⚠️ Model not found. Trying alternative model...",
                "requirements": []
            }
        else:
            return {
                "summary": f"⚠️ AI Analysis Error: {error_msg[:100]}...",
                "requirements": []
            }

# --- 4. APP STATE ---
if 'resume_text' not in st.session_state: 
    st.session_state.resume_text = ""
if 'jobs_df' not in st.session_state: 
    st.session_state.jobs_df = pd.DataFrame()
if 'matches_df' not in st.session_state: 
    st.session_state.matches_df = pd.DataFrame()
if 'resume_uploaded' not in st.session_state: 
    st.session_state.resume_uploaded = False
if 'showing_desc' not in st.session_state: 
    st.session_state.showing_desc = {}
if 'last_uploaded_file' not in st.session_state: 
    st.session_state.last_uploaded_file = None
if 'show_full_resume' not in st.session_state: 
    st.session_state.show_full_resume = False
if 'job_analyses' not in st.session_state: 
    st.session_state.job_analyses = {}  # Store AI analyses by job_id

# --- 5. MAIN UI LAYOUT ---

st.markdown("""
<div style='text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%); border-radius: 0 0 20px 20px; margin-bottom: 2rem;'>
    <h1 style='color: white; margin: 0; font-size: 3rem;'>🤖 Resume Matcher Pro</h1>
    <p style='color: rgba(255,255,255,0.8); margin-top: 0.5rem; font-size: 1.1rem;'>AI-Powered Job Matching with Google Gemini</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 🔍 Search Configuration")
    
    # AI Status
    if GEMINI_ENABLED:
        st.success("✅ Google Gemini AI Enabled")
        st.caption("AI summaries available for jobs")
    else:
        st.warning("⚠️ Google Gemini AI Disabled")
        st.caption("Set GOOGLE_API_KEY in .env file")
        st.info("""
        Get API key from:
        https://makersuite.google.com/app/apikey
        """)
    
    st.markdown("---")
    
    # Resume Status
    if st.session_state.resume_uploaded:
        resume_len = len(st.session_state.resume_text)
        word_count = len(st.session_state.resume_text.split())
        st.success(f"✅ Resume Loaded ({word_count} words)")
    else:
        st.warning("📄 Upload Resume Required")
    
    st.markdown("---")
    
    # Search Parameters
    job_title = st.text_input("Job Title", placeholder="e.g., Software Engineer", value="Software Engineer")
    location = st.text_input("Location", placeholder="e.g., Remote", value="Remote")
    
    search_col1, search_col2 = st.columns([2, 1])
    with search_col1:
        search_button = st.button("🚀 Search Jobs", type="primary", use_container_width=True)
    
    with search_col2:
        if st.session_state.matches_df.empty:
            analyze_button_disabled = True
        else:
            analyze_button_disabled = False
        
        analyze_button = st.button("✨ AI Analyze", 
                                 disabled=analyze_button_disabled,
                                 use_container_width=True,
                                 help="Get AI summaries for all jobs")
    
    if search_button and st.session_state.resume_uploaded:
        with st.spinner("Searching for jobs..."):
            try:
                # Clear previous analyses
                st.session_state.job_analyses = {}
                
                # 1. Search API
                api = JobSearchAPI()
                jobs = api.search_jobs(query=job_title, location=location, num_pages=1)
                
                # Check if we actually got jobs
                if not jobs.empty:
                    st.session_state.jobs_df = jobs
                    
                    # 2. Match Logic
                    matcher = JobMatcher()
                    matches = matcher.match_resume_to_jobs(
                        st.session_state.resume_text,
                        st.session_state.jobs_df,
                        top_n=10
                    )
                    st.session_state.matches_df = matches
                    st.success(f"✅ Found {len(matches)} matching jobs!")
                    
                    # Force rerun to show matches tab
                    st.rerun()
                else:
                    st.session_state.matches_df = pd.DataFrame()
                    st.error("❌ No jobs found. Try a broader search term.")
                    
            except Exception as e:
                st.error(f"❌ Search Error: {str(e)}")
    elif search_button:
        st.warning("Please upload a resume first!")
    
    # Analyze All Jobs button action
    if analyze_button and not st.session_state.matches_df.empty:
        st.info("Click 'Analyze' buttons on individual job cards to get AI summaries.")
    
    # Clear button
    if st.session_state.resume_uploaded:
        st.markdown("---")
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.resume_text = ""
            st.session_state.resume_uploaded = False
            st.session_state.matches_df = pd.DataFrame()
            st.session_state.job_analyses = {}
            st.session_state.last_uploaded_file = None
            st.rerun()

# Logic to determine active tab
if not st.session_state.matches_df.empty:
    tab1, tab2 = st.tabs(["🎯 Job Matches", "📄 Upload Resume"])
    matches_tab = tab1
    upload_tab = tab2
else:
    tab1, tab2 = st.tabs(["📄 Upload Resume", "🎯 Job Matches"])
    upload_tab = tab1
    matches_tab = tab2

# --- UPLOAD TAB ---
with upload_tab:
    st.markdown("### 📤 Upload Your Resume")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader("Choose PDF or DOCX file", 
                                        type=['pdf', 'docx'], 
                                        label_visibility="collapsed",
                                        help="Upload your resume in PDF or DOCX format")
    
    with col2:
        if GEMINI_ENABLED:
            st.markdown("""
            <div style='margin-top: 1rem; padding: 0.5rem; background: rgba(59, 130, 246, 0.1); border-radius: 8px;'>
            <small>✅ AI Enabled</small><br>
            <small>Job summaries available</small>
            </div>
            """, unsafe_allow_html=True)
    
    if uploaded_file and (st.session_state.last_uploaded_file != uploaded_file.name):
        with st.spinner("Parsing your resume..."):
            try:
                if uploaded_file.name.endswith('.pdf'):
                    text = extract_text_from_pdf(uploaded_file)
                else:
                    text = extract_text_from_docx(uploaded_file)
                
                if text and len(clean_text(text)) > 50:
                    st.session_state.resume_text = clean_text(text)
                    st.session_state.resume_uploaded = True
                    st.session_state.last_uploaded_file = uploaded_file.name
                    st.success("✅ Resume successfully uploaded!")
                    st.rerun()
                else:
                    st.error("❌ File is empty or unreadable. Please upload a valid resume.")
            except Exception as e:
                st.error(f"❌ Error parsing file: {e}")

    # Preview Section
    if st.session_state.resume_uploaded:
        st.markdown("### 👁️ Resume Preview")
        
        preview_col1, preview_col2 = st.columns([1, 4])
        with preview_col1:
            toggle_label = "Show Full" if not st.session_state.show_full_resume else "Show Preview"
            if st.button(toggle_label, use_container_width=True):
                st.session_state.show_full_resume = not st.session_state.show_full_resume
                st.rerun()
        
        with preview_col2:
            char_count = len(st.session_state.resume_text)
            word_count = len(st.session_state.resume_text.split())
            st.caption(f"📊 {word_count} words, {char_count} characters")
        
        preview = st.session_state.resume_text
        if not st.session_state.show_full_resume and len(preview) > 1000:
            preview = preview[:1000] + "\n\n... [truncated]"
            
        st.markdown(f"<div class='preview-box'>{preview}</div>", unsafe_allow_html=True)

# --- MATCHES TAB ---
with matches_tab:
    if st.session_state.matches_df.empty:
        st.info("👈 Upload your resume and search for jobs to see matching results.")
        
        # Show example if no resume uploaded
        if not st.session_state.resume_uploaded:
            st.markdown("---")
            with st.expander("ℹ️ How to get started"):
                st.markdown("""
                1. **Upload your resume** (PDF or DOCX)
                2. **Enter job title** and location in sidebar
                3. **Click 'Search Jobs'** to find opportunities
                4. **Use AI Analysis** to get job summaries
                
                **Features:**
                - AI-powered job matching
                - Google Gemini summaries
                - Skill requirement analysis
                - One-click job applications
                """)
    else:
        total_matches = len(st.session_state.matches_df)
        avg_score = st.session_state.matches_df['match_score'].mean() if 'match_score' in st.session_state.matches_df.columns else 0
        
        # Header with stats
        st.markdown(f"""
        <div style='background: rgba(30, 41, 59, 0.5); padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <h3 style='margin: 0; color: #f8fafc;'>🎯 {total_matches} Job Matches Found</h3>
                    <p style='margin: 0.2rem 0 0 0; color: #94a3b8;'>Average match score: {avg_score:.1f}%</p>
                </div>
                <div style='text-align: right;'>
                    <div style='color: #60a5fa; font-size: 0.9rem;'>Google Gemini AI Ready</div>
                    <div style='color: #94a3b8; font-size: 0.8rem;'>Click "Analyze" for summaries</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Sort options
        sort_col1, sort_col2 = st.columns([1, 5])
        with sort_col1:
            sort_option = st.selectbox("Sort by", ["Best Match", "Job Title", "Company"], label_visibility="collapsed")
        
        # Sort the dataframe
        if sort_option == "Best Match":
            sorted_df = st.session_state.matches_df.sort_values('match_score', ascending=False)
        elif sort_option == "Job Title":
            sorted_df = st.session_state.matches_df.sort_values('job_title')
        else:
            sorted_df = st.session_state.matches_df.sort_values('employer_name')
        
        # Display Loop
        for idx, row in sorted_df.iterrows():
            score = row.get('match_score', 0)
            job_desc = row.get('job_description', '')
            job_title = row.get('job_title', 'Job')
            employer = row.get('employer_name', 'Company')
            location_txt = row.get('location_display', 'Remote')
            
            # Create a unique key for this job
            job_key = f"{job_title}_{employer}_{idx}"
            
            # Check if we already have AI analysis for this job
            has_ai_analysis = job_key in st.session_state.job_analyses
            
            # --- RENDER CARD ---
            st.markdown('<div class="job-card">', unsafe_allow_html=True)
            
            # 1. Header Row with AI status
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"<h3 style='color:#f8fafc; margin:0; font-size:1.4rem;'>{job_title}</h3>", unsafe_allow_html=True)
                st.markdown(f"<div style='color:#94a3b8; font-size:1rem; margin-top:0.2rem;'>🏢 <b>{employer}</b> • 📍 {location_txt}</div>", unsafe_allow_html=True)
            
            with c2:
                s_class = "high-match" if score >= 75 else "med-match" if score >= 50 else "low-match"
                st.markdown(f"""
                <div class='score-badge {s_class}'>
                    <div class='score-val'>{score:.0f}%</div>
                    <div class='score-lbl'>Match</div>
                </div>
                """, unsafe_allow_html=True)
            
            with c3:
                if has_ai_analysis:
                    st.markdown("""
                    <div class='score-badge' style='border-color: rgba(52, 211, 153, 0.3);'>
                        <div class='score-val' style='color: #34d399; font-size: 1.2rem;'>✅</div>
                        <div class='score-lbl'>AI Analyzed</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # 2. Meta Data Grid
            st.markdown(f"""
            <div class='meta-grid'>
                <div class='meta-item'><strong>📍 Location</strong>{location_txt}</div>
                <div class='meta-item'><strong>💼 Type</strong>{row.get('job_employment_type', 'Full-time')}</div>
                <div class='meta-item'><strong>💰 Salary</strong>{row.get('salary_display', 'Not specified')}</div>
                <div class='meta-item'><strong>📅 Posted</strong>{row.get('job_posted_at', 'Recent')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 3. AI ANALYSIS SECTION
            if has_ai_analysis:
                # Display AI analysis
                ai_data = st.session_state.job_analyses[job_key]
                
                st.markdown('<div class="ai-insight-card">', unsafe_allow_html=True)
                
                # Check for error messages
                if "⚠️" in ai_data.get('summary', ''):
                    st.markdown(f"""
                    <div class='summary-text' style='border-left-color: #f87171; color: #fca5a5;'>
                        {ai_data.get('summary')}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Show AI Summary
                    st.markdown(f"""
                    <div class='section-title'>🤖 AI Summary</div>
                    <div class='summary-text'>{ai_data.get('summary', 'No summary available.')}</div>
                    """, unsafe_allow_html=True)
                    
                    # Show Requirements
                    requirements = ai_data.get('requirements', [])
                    if requirements:
                        list_html = "".join([f"<li>{req}</li>" for req in requirements[:5]]) 
                        st.markdown(f"""
                        <div class='section-title'>📋 Key Requirements</div>
                        <ul class='clean-list'>
                            {list_html}
                        </ul>
                        """, unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # Show Analyze Button
                st.markdown("<br>", unsafe_allow_html=True)
                analyze_col1, analyze_col2 = st.columns([3, 1])
                
                with analyze_col2:
                    if GEMINI_ENABLED:
                        if st.button(f"✨ Analyze with AI", key=f"analyze_{idx}", use_container_width=True):
                            with st.spinner("🤖 AI is analyzing this job..."):
                                # Get AI analysis
                                ai_result = analyze_job_with_gemini(job_desc, job_title, employer)
                                
                                # Store in session state
                                st.session_state.job_analyses[job_key] = ai_result
                                
                                # Show success message
                                st.success("✅ Analysis complete!")
                                
                                # Rerun to show results
                                st.rerun()
                    else:
                        st.warning("AI Disabled", help="Enable Gemini AI in .env file")
            
            # 4. Action Buttons
            st.markdown("<div style='margin-top: 1.5rem;'>", unsafe_allow_html=True)
            b1, b2, b3 = st.columns([1, 1, 1])
            
            with b1:
                if row.get('job_apply_link'):
                    st.link_button("🚀 Apply Now", 
                                 row['job_apply_link'], 
                                 use_container_width=True,
                                 help="Open job application page")
            
            with b2:
                toggle_key = f"toggle_{idx}"
                btn_txt = "❌ Hide Details" if st.session_state.showing_desc.get(f"job_{idx}") else "📄 Show Details"
                if st.button(btn_txt, key=toggle_key, use_container_width=True):
                    st.session_state.showing_desc[f"job_{idx}"] = not st.session_state.showing_desc.get(f"job_{idx}", False)
                    st.rerun()
            
            with b3:
                if st.button("📋 Copy Info", key=f"copy_{idx}", use_container_width=True):
                    job_info = f"""Job: {job_title}
Company: {employer}
Location: {location_txt}
Match Score: {score}%
Link: {row.get('job_apply_link', 'N/A')}"""
                    st.code(job_info, language=None)
                    st.toast("Job info copied!", icon="📋")
            
            # Toggle Content - Job Description
            if st.session_state.showing_desc.get(f"job_{idx}", False):
                st.markdown(f"<div class='job-description-box'>{job_desc}</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)  # End Actions
            st.markdown("</div>", unsafe_allow_html=True)  # End Card
            
            # Add separator between cards (except last one)
            if idx < len(sorted_df) - 1:
                st.markdown("<hr style='border-color: #334155; margin: 1rem 0;'>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6b7280; padding: 1rem 0;'>
    <div><strong>Resume Matcher Pro</strong> • Powered by Google Gemini AI</div>
    <div style='font-size: 0.8rem; margin-top: 0.5rem;'>
        Upload resume → Search jobs → Get AI-powered summaries → Apply instantly
    </div>
</div>
""", unsafe_allow_html=True)