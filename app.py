import streamlit as st
import pandas as pd
import os
from datetime import datetime
import re

# Import our modules
from job_api import JobSearchAPI
from job_matcher_simple import JobMatcher
from resume_parser_simple import extract_text_from_pdf, extract_text_from_docx, clean_text

# Set page config
st.set_page_config(
    page_title="Resume Matcher",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Web Dark Theme CSS
st.markdown("""
<style>
    /* Main background - comfortable dark gray like modern web apps */
    .stApp {
        background-color: #1a1a1a;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1f1f1f;
        border-right: 1px solid #333333;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
        color: #60a5fa;
        font-weight: 700;
        margin-top: 1rem;
    }
    
    /* Card styling */
    .job-card {
        background: #242424;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid #333333;
        transition: all 0.3s ease;
        position: relative;
    }
    
    .job-card:hover {
        transform: translateY(-3px);
        border-color: #60a5fa;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }
    
    /* Score badge styling */
    .score-badge {
        background: rgba(59, 130, 246, 0.1);
        border-radius: 10px;
        padding: 0.8rem;
        text-align: center;
        border: 2px solid;
    }
    
    .score-high { 
        color: #34d399;
        border-color: #34d399;
    }
    
    .score-medium { 
        color: #fbbf24;
        border-color: #fbbf24;
    }
    
    .score-low { 
        color: #f87171;
        border-color: #f87171;
    }
    
    /* Text colors */
    .white-text { color: #e5e7eb; }
    .gray-text { color: #9ca3af; }
    .blue-text { color: #60a5fa; }
    
    /* Bullet points styling */
    .job-bullets {
        color: #d1d5db;
        font-size: 0.95rem;
        line-height: 1.8;
        margin: 1rem 0;
    }
    
    .job-bullets li {
        margin-bottom: 0.5rem;
    }
    
    /* Info section styling */
    .info-section {
        background: #1f1f1f;
        border-radius: 8px;
        padding: 1rem;
        margin-top: 1rem;
        border-left: 3px solid #60a5fa;
    }
    
    .info-row {
        display: flex;
        align-items: center;
        margin: 0.5rem 0;
        color: #d1d5db;
        font-size: 0.9rem;
    }
    
    .info-label {
        color: #60a5fa;
        font-weight: 600;
        min-width: 120px;
    }
    
    .skill-tag {
        display: inline-block;
        background: rgba(96, 165, 250, 0.15);
        color: #93c5fd;
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        margin: 0.3rem 0.3rem 0.3rem 0;
        font-size: 0.85rem;
        font-weight: 500;
        border: 1px solid rgba(96, 165, 250, 0.3);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        padding: 0.6rem 1.5rem;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        transform: translateY(-2px);
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #242424;
        color: #e5e7eb;
        border: 1px solid #333333;
        border-radius: 8px;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #60a5fa;
        box-shadow: 0 0 0 1px #60a5fa;
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: #242424;
        border: 2px dashed #333333;
        border-radius: 10px;
        padding: 2rem;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: #60a5fa;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #242424;
        border-radius: 8px 8px 0 0;
        color: #9ca3af;
        padding: 12px 24px;
        font-weight: 600;
        border: 1px solid #333333;
    }
    
    .stTabs [aria-selected="true"] {
        background: #3b82f6;
        color: white;
        border-color: #3b82f6;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #60a5fa;
        font-size: 2rem;
        font-weight: 700;
    }
    
    [data-testid="stMetricLabel"] {
        color: #9ca3af;
        font-weight: 600;
    }
    
    /* Select box */
    .stSelectbox > div > div {
        background-color: #242424;
        border-color: #333333;
        border-radius: 8px;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #242424;
        border-radius: 8px;
        color: #e5e7eb;
        font-weight: 600;
    }
    
    .streamlit-expanderContent {
        background-color: #1f1f1f;
        border: 1px solid #333333;
        max-height: 400px;
        overflow-y: auto;
    }
    
    /* Divider */
    hr {
        border-color: #333333;
        margin: 2rem 0;
    }
    
    /* Remove watermark */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Info card */
    .info-card {
        background: #242424;
        border-radius: 10px;
        padding: 1.2rem;
        border: 1px solid #333333;
        margin: 1rem 0;
    }
    
    /* Preview text box */
    .preview-box {
        background: #1f1f1f;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 1rem;
        color: #d1d5db;
        font-family: monospace;
        font-size: 0.85rem;
        line-height: 1.6;
        white-space: pre-wrap;
        max-height: 400px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to extract skills from job description
def extract_skills(description):
    if not description or pd.isna(description):
        return []
    
    # Common skill keywords to look for
    skill_patterns = [
        r'\b(?:Python|Java|JavaScript|TypeScript|C\+\+|C#|Ruby|Go|Rust|Swift|Kotlin|PHP|Scala)\b',
        r'\b(?:React|Angular|Vue|Node\.js|Django|Flask|Spring|Express|FastAPI|Next\.js)\b',
        r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|Git|CI/CD|Terraform)\b',
        r'\b(?:SQL|PostgreSQL|MongoDB|MySQL|Redis|Oracle|Cassandra|DynamoDB)\b',
        r'\b(?:Machine Learning|AI|Data Science|Analytics|Statistics|Deep Learning)\b',
        r'\b(?:REST|API|Microservices|Agile|Scrum|DevOps|GraphQL)\b',
        r'\b(?:HTML|CSS|Sass|Tailwind|Bootstrap|Material UI)\b',
        r'\b(?:TensorFlow|PyTorch|Pandas|NumPy|Scikit-learn|Keras)\b',
    ]
    
    skills = set()
    
    for pattern in skill_patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        skills.update(matches)
    
    return list(skills)[:12]  # Return max 12 skills

# Helper function to extract key requirements
def extract_key_points(description):
    if not description or pd.isna(description):
        return ["No description available"]
    
    lines = description.split('\n')
    points = []
    
    # Look for requirement sections
    req_keywords = ['responsibilities', 'requirements', 'qualifications', 'you will', 'required', 'must have', 'should have']
    in_requirements_section = False
    
    for line in lines:
        line = line.strip()
        line_lower = line.lower()
        
        # Check if we're entering a requirements section
        if any(keyword in line_lower for keyword in req_keywords):
            in_requirements_section = True
            continue
        
        # If we're in requirements section or line looks like a requirement
        if in_requirements_section or line.startswith(('-', '•', '*', '●')) or (line and line[0].isdigit() and len(line) > 30):
            clean_line = re.sub(r'^[•\-*●\d.)\s]+', '', line).strip()
            
            # Filter out company descriptions and generic statements
            skip_phrases = ['we are', 'we design', 'our diverse', 'our company', 'we create', 'we offer', 
                          'about us', 'who we are', 'our mission', 'our vision', 'we believe']
            
            if (len(clean_line) > 25 and len(clean_line) < 200 and 
                not any(phrase in clean_line.lower() for phrase in skip_phrases)):
                points.append(clean_line)
                if len(points) >= 6:
                    break
    
    # If still no points, try extracting action-oriented sentences
    if not points:
        sentences = description.split('.')
        action_words = ['develop', 'design', 'manage', 'build', 'create', 'lead', 'work', 
                       'collaborate', 'implement', 'maintain', 'support', 'analyze', 'require']
        
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 30 and any(word in sent.lower() for word in action_words):
                points.append(sent)
                if len(points) >= 5:
                    break
    
    return points if points else ["Detailed requirements available - click to view full description"]

# Initialize session state
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = ""
if 'jobs_df' not in st.session_state:
    st.session_state.jobs_df = pd.DataFrame()
if 'matches_df' not in st.session_state:
    st.session_state.matches_df = pd.DataFrame()
if 'resume_uploaded' not in st.session_state:
    st.session_state.resume_uploaded = False

# Header
st.markdown("<h1 style='text-align: center; color: #e5e7eb;'>🤖 Resume Matcher</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #9ca3af; text-align: center; font-size: 1.1rem; margin-bottom: 2rem;'>Upload your resume • Search & match jobs automatically • Land your dream role</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 🔍 Search & Match Jobs")
    
    # Check if resume is uploaded
    if not st.session_state.resume_uploaded:
        st.warning("⚠️ Upload your resume first!")
    
    job_title = st.text_input("Job Title", "", help="Enter the job title you're looking for")
    location = st.text_input("Location", "", help="Enter location")
    
    # Combined search and match button
    search_button_disabled = not st.session_state.resume_uploaded
    
    if st.button("🚀 Search & Match Jobs", type="primary", use_container_width=True, disabled=search_button_disabled):
        with st.spinner("🔎 Searching for jobs and matching with your resume..."):
            try:
                # Step 1: Search for jobs
                api = JobSearchAPI()
                jobs = api.search_jobs(
                    query=job_title,
                    location=location,
                    num_pages=2
                )
                
                if not jobs.empty:
                    st.session_state.jobs_df = jobs
                    st.success(f"✅ Found {len(jobs)} jobs!")
                    
                    # Step 2: Automatically match jobs with resume
                    with st.spinner("🤖 Matching jobs with your resume..."):
                        matcher = JobMatcher()
                        matches = matcher.match_resume_to_jobs(
                            st.session_state.resume_text,
                            st.session_state.jobs_df,
                            top_n=15
                        )
                        st.session_state.matches_df = matches
                        st.success(f"✅ Matched {len(matches)} jobs!")
                        st.balloons()
                        # Switch to matches tab by rerunning
                        st.rerun()
                else:
                    st.error("❌ No jobs found")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    st.divider()
    
    # Resume stats
    if st.session_state.resume_uploaded:
        st.markdown("## 📊 Resume Stats")
        words = len(st.session_state.resume_text.split())
        chars = len(st.session_state.resume_text)
        st.metric("Word Count", f"{words:,}")
        st.metric("Characters", f"{chars:,}")
        st.markdown(f"<div class='info-card'><div style='color: #34d399; font-weight: 600;'>✅ Resume Loaded</div></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='info-card'><div style='color: #9ca3af;'>📄 No resume uploaded yet</div></div>", unsafe_allow_html=True)
    
    if not st.session_state.jobs_df.empty:
        st.divider()
        st.markdown("## 💼 Jobs Available")
        st.metric("Total Jobs", len(st.session_state.jobs_df))

# Main content - Control tab display
if not st.session_state.matches_df.empty:
    # If we have matches, show matches tab first
    tab1, tab2 = st.tabs(["🎯 Job Matches", "📄 Upload Resume"])
    show_matches_first = True
else:
    # Otherwise show upload tab first
    tab1, tab2 = st.tabs(["📄 Upload Resume", "🎯 Job Matches"])
    show_matches_first = False

# Determine which tab content to show where
if show_matches_first:
    upload_tab = tab2
    matches_tab = tab1
else:
    upload_tab = tab1
    matches_tab = tab2

# Upload Resume Tab Content
with upload_tab:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📤 Upload Your Resume")
        st.markdown("<p class='gray-text'>Supported formats: PDF, DOCX</p>", unsafe_allow_html=True)
        
        # File upload
        uploaded_file = st.file_uploader("Choose your resume file", type=['pdf', 'docx'], label_visibility="collapsed", key="file_uploader")
        
        if uploaded_file:
            try:
                with st.spinner("📄 Parsing resume..."):
                    if uploaded_file.name.lower().endswith('.pdf'):
                        resume_text = extract_text_from_pdf(uploaded_file)
                    else:
                        resume_text = extract_text_from_docx(uploaded_file)
                    
                    if resume_text:
                        st.session_state.resume_text = clean_text(resume_text)
                        st.session_state.resume_uploaded = True
                        st.success(f"✅ Resume uploaded successfully! ({uploaded_file.name})")
                        
                        # Show full preview
                        st.markdown("---")
                        st.markdown("### 👁️ Parsed Resume Preview")
                        st.markdown("<div class='preview-box'>", unsafe_allow_html=True)
                        st.text(st.session_state.resume_text)
                        st.markdown("</div>", unsafe_allow_html=True)
                    else:
                        st.error("❌ Could not read file content")
                    
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
        
        # Show preview if resume already loaded (no new file uploaded)
        elif st.session_state.resume_uploaded and st.session_state.resume_text:
            st.info("✅ Resume already loaded. Upload a new file to replace it.")
            st.markdown("---")
            st.markdown("### 👁️ Current Resume Preview")
            st.markdown("<div class='preview-box'>", unsafe_allow_html=True)
            st.text(st.session_state.resume_text)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Text paste option
        st.markdown("---")
        st.markdown("### ✍️ Or Paste Resume Text")
        resume_text = st.text_area("Paste your resume here:", height=200, placeholder="Paste your resume text here...", key="resume_textarea")
        
        if st.button("💾 Save Pasted Text", use_container_width=True):
            if resume_text and len(resume_text) > 50:
                st.session_state.resume_text = clean_text(resume_text)
                st.session_state.resume_uploaded = True
                st.success("✅ Resume text saved successfully!")
                st.rerun()
            else:
                st.warning("⚠️ Please paste at least 50 characters")
    
    with col2:
        st.markdown("### 💡 How It Works")
        st.markdown("""
        <div class='info-card'>
        <div style='color: #9ca3af; font-size: 0.9rem; line-height: 1.8;'>
        <strong style='color: #60a5fa;'>Step 1:</strong> Upload your resume<br><br>
        <strong style='color: #60a5fa;'>Step 2:</strong> Enter job title and location in sidebar<br><br>
        <strong style='color: #60a5fa;'>Step 3:</strong> Click "Search & Match Jobs"<br><br>
        <strong style='color: #60a5fa;'>Step 4:</strong> View matched jobs automatically!
        </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### ✨ Tips")
        st.markdown("""
        <div class='info-card'>
        <div style='color: #9ca3af; font-size: 0.9rem;'>
        • Include detailed work experience<br>
        • List all relevant skills<br>
        • Mention certifications<br>
        • Use industry keywords
        </div>
        </div>
        """, unsafe_allow_html=True)

# Job Matches Tab Content
with matches_tab:
    if st.session_state.matches_df.empty:
        st.markdown("""
        <div style='text-align: center; padding: 4rem 2rem;'>
            <div style='font-size: 4rem; margin-bottom: 1rem;'>🎯</div>
            <h2 style='color: #60a5fa; margin-bottom: 1rem;'>No Matches Yet</h2>
            <p style='color: #9ca3af; font-size: 1.1rem;'>Upload your resume and click "Search & Match Jobs" in the sidebar</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Stats header
        total = len(st.session_state.matches_df)
        avg_score = st.session_state.matches_df['match_score'].mean()
        high_matches = len(st.session_state.matches_df[st.session_state.matches_df['match_score'] >= 75])
        
        st.markdown("### 📊 Match Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Matches", total)
        with col2:
            st.metric("Avg. Score", f"{avg_score:.1f}%")
        with col3:
            st.metric("High Matches", high_matches)
        with col4:
            best_score = st.session_state.matches_df['match_score'].max()
            st.metric("Best Score", f"{best_score:.1f}%")
        
        st.markdown("---")
        
        # Sort and filter options
        col_sort, col_filter = st.columns([1, 1])
        
        with col_sort:
            sort_by = st.selectbox("Sort by:", ["Best Match", "Company"])
        
        with col_filter:
            min_score = st.slider("Minimum Match Score:", 0, 100, 0, 5)
        
        # Sort and filter the data
        display_df = st.session_state.matches_df.copy()
        display_df = display_df[display_df['match_score'] >= min_score]
        
        if sort_by == "Best Match":
            display_df = display_df.sort_values('match_score', ascending=False)
        elif sort_by == "Company":
            display_df = display_df.sort_values('employer_name')
        
        st.markdown(f"### 💼 Showing {len(display_df)} Jobs")
        
        # Display job cards
        for idx, row in display_df.iterrows():
            score = row.get('match_score', 0)
            
            # Determine score styling
            if score >= 75:
                score_class = "score-high"
                score_icon = "🟢"
                score_label = "Excellent"
            elif score >= 50:
                score_class = "score-medium"
                score_icon = "🟡"
                score_label = "Good"
            else:
                score_class = "score-low"
                score_icon = "🔴"
                score_label = "Fair"
            
            # Get job details
            job_title = row.get('job_title', 'Position')
            company = row.get('employer_name', 'Company')
            job_desc = row.get('job_description', '')
            
            # Get location details - improved formatting
            location_parts = []
            city = row.get('job_city', '')
            state = row.get('job_state', '')
            country = row.get('job_country', '')
            
            if pd.notna(city) and str(city).strip() and len(str(city).strip()) > 1:
                location_parts.append(str(city).strip())
            if pd.notna(state) and str(state).strip() and len(str(state).strip()) > 1:
                location_parts.append(str(state).strip())
            if pd.notna(country) and str(country).strip() and len(str(country).strip()) > 1:
                country_str = str(country).strip()
                # Don't add country if it's just a code and we already have city/state
                if len(country_str) > 2 or not location_parts:
                    location_parts.append(country_str)
            
            location = ', '.join(location_parts) if location_parts else 'Remote / Location not specified'
            
            # Get employment type - improved handling
            emp_type = row.get('job_employment_type', '')
            if pd.isna(emp_type) or not str(emp_type).strip() or str(emp_type).strip().lower() == 'nan':
                emp_type = 'Full-time (Type not specified)'
            else:
                emp_type = str(emp_type).strip()
            
            # Extract key points and skills
            key_points = extract_key_points(job_desc)
            skills = extract_skills(job_desc)
            
            # Apply link
            apply_link = row.get('job_apply_link', '#')
            
            # Create job card
            st.markdown('<div class="job-card">', unsafe_allow_html=True)
            
            # Top row: Title and Score
            col_title, col_score = st.columns([3, 1])
            
            with col_title:
                st.markdown(f"<h3 style='color: #e5e7eb; margin-bottom: 0.5rem;'>{job_title}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='color: #9ca3af; margin: 0; font-size: 1rem;'>🏢 {company}</p>", unsafe_allow_html=True)
            
            with col_score:
                st.markdown(f"""
                <div class='score-badge {score_class}'>
                    <div style='font-size: 2rem; font-weight: bold; margin-bottom: 0.2rem;'>{score:.0f}%</div>
                    <div style='font-size: 0.85rem;'>{score_icon} {score_label}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Job info section
            st.markdown("<div class='info-section'>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class='info-row'>
                <span class='info-label'>📍 Location:</span>
                <span>{location}</span>
            </div>
            <div class='info-row'>
                <span class='info-label'>💼 Position Type:</span>
                <span>{emp_type}</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Key requirements section
            st.markdown("<div style='margin-top: 1rem;'><p style='color: #60a5fa; font-weight: 600; font-size: 0.95rem; margin-bottom: 0.5rem;'>📋 KEY REQUIREMENTS</p></div>", unsafe_allow_html=True)
            
            bullets_html = "<ul class='job-bullets' style='margin-left: 1.5rem;'>"
            for point in key_points:
                bullets_html += f"<li>{point}</li>"
            bullets_html += "</ul>"
            st.markdown(bullets_html, unsafe_allow_html=True)
            
            # Skills section
            if skills:
                st.markdown("<div style='margin-top: 1rem;'><p style='color: #60a5fa; font-weight: 600; font-size: 0.95rem; margin-bottom: 0.8rem;'>🎯 SKILLS WE ARE LOOKING FOR</p></div>", unsafe_allow_html=True)
                
                skills_html = "<div>"
                for skill in skills:
                    skills_html += f"<span class='skill-tag'>{skill}</span>"
                skills_html += "</div>"
                st.markdown(skills_html, unsafe_allow_html=True)
            
            # Action buttons - No nested expanders
            st.markdown("<div style='margin-top: 1.5rem;'>", unsafe_allow_html=True)
            
            col_btn1, col_btn2 = st.columns([1, 1])
            
            with col_btn1:
                if apply_link and apply_link != '#':
                    st.markdown(
                        f'<a href="{apply_link}" target="_blank" style="text-decoration: none;">'
                        '<button style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; padding: 0.8rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; width: 100%; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2); transition: all 0.3s; font-size: 1rem;">Apply Now →</button>'
                        '</a>',
                        unsafe_allow_html=True
                    )
            
            with col_btn2:
                # Use a regular button with a unique key to toggle description
                if st.button("📄 View Full Description", key=f"view_desc_{idx}", use_container_width=True):
                    # Store which job description to show
                    if 'showing_desc' not in st.session_state:
                        st.session_state.showing_desc = {}
                    
                    # Toggle the description visibility
                    job_key = f"job_{idx}"
                    st.session_state.showing_desc[job_key] = not st.session_state.showing_desc.get(job_key, False)
            
            # Show description if toggled
            if 'showing_desc' in st.session_state and st.session_state.showing_desc.get(f"job_{idx}", False):
                if job_desc and len(str(job_desc).strip()) > 10:
                    st.markdown(f"""
                    <div style='color: #d1d5db; font-size: 0.9rem; line-height: 1.6; 
                              padding: 1rem; background: #1f1f1f; 
                              border-radius: 8px; max-height: 300px; overflow-y: auto; margin-top: 1rem;
                              border: 1px solid #333333;'>
                        {job_desc}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("<div style='color: #9ca3af; margin-top: 1rem;'>No detailed description available.</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)  # Close job-card
        
        # Export option
        st.markdown("---")
        col_export1, col_export2, col_export3 = st.columns([1, 1, 2])
        
        with col_export1:
            if st.button("📥 Download CSV", use_container_width=True):
                csv = display_df.to_csv(index=False)
                st.download_button(
                    "⬇️ Click to Download",
                    csv,
                    f"job_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 2rem 0;'>
    <p style='color: #6b7280; font-size: 0.9rem;'>Resume Matcher • Powered by AI</p>
    <p style='color: #4b5563; font-size: 0.8rem;'>Find your perfect job match with intelligent resume analysis</p>
</div>
""", unsafe_allow_html=True)