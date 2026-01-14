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
    
    .skills-section {
        background: #1f1f1f;
        border-radius: 8px;
        padding: 1rem;
        margin-top: 1rem;
        border-left: 3px solid #60a5fa;
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
</style>
""", unsafe_allow_html=True)

# Helper function to extract skills from job description
def extract_skills(description):
    if not description or pd.isna(description):
        return []
    
    # Common skill keywords to look for
    skill_patterns = [
        r'\b(?:Python|Java|JavaScript|TypeScript|C\+\+|C#|Ruby|Go|Rust|Swift|Kotlin)\b',
        r'\b(?:React|Angular|Vue|Node\.js|Django|Flask|Spring|Express)\b',
        r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|Git|CI/CD)\b',
        r'\b(?:SQL|PostgreSQL|MongoDB|MySQL|Redis|Oracle)\b',
        r'\b(?:Machine Learning|AI|Data Science|Analytics|Statistics)\b',
        r'\b(?:REST|API|Microservices|Agile|Scrum|DevOps)\b',
        r'\b(?:HTML|CSS|Sass|Tailwind|Bootstrap)\b',
        r'\b(?:TensorFlow|PyTorch|Pandas|NumPy|Scikit-learn)\b',
    ]
    
    skills = set()
    desc_lower = description.lower()
    
    for pattern in skill_patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        skills.update(matches)
    
    return list(skills)[:10]  # Return max 10 skills

# Helper function to extract key requirements
def extract_key_points(description):
    if not description or pd.isna(description):
        return ["No description available"]
    
    # Try to find bullet points or split by common delimiters
    lines = description.split('\n')
    points = []
    
    for line in lines:
        line = line.strip()
        # Look for lines that start with bullets, numbers, or are substantive
        if line and (line[0] in ['•', '-', '*', '●'] or line[0].isdigit() or len(line) > 30):
            # Clean up the line
            clean_line = re.sub(r'^[•\-*●\d.)\s]+', '', line).strip()
            if len(clean_line) > 20 and len(clean_line) < 150:
                points.append(clean_line)
                if len(points) >= 5:  # Limit to 5 points
                    break
    
    if not points:
        # If no bullet points found, extract first few sentences
        sentences = description.split('.')
        for sent in sentences[:3]:
            sent = sent.strip()
            if len(sent) > 30:
                points.append(sent)
    
    return points if points else ["View full description for details"]

# Initialize session state
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = ""
if 'jobs_df' not in st.session_state:
    st.session_state.jobs_df = pd.DataFrame()
if 'matches_df' not in st.session_state:
    st.session_state.matches_df = pd.DataFrame()
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = 0

# Header
st.markdown("<h1 style='text-align: center; color: #e5e7eb;'>🤖 Resume Matcher</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #9ca3af; text-align: center; font-size: 1.1rem; margin-bottom: 2rem;'>Upload your resume • Find perfect matching jobs • Land your dream role</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 🔍 Job Search")
    
    job_title = st.text_input("Job Title", "software engineer", help="Enter the job title you're looking for")
    location = st.text_input("Location", "United States", help="Enter location or 'Remote'")
    
    if st.button("🚀 Search Jobs", type="primary", use_container_width=True):
        with st.spinner("🔎 Searching for jobs..."):
            try:
                api = JobSearchAPI()
                jobs = api.search_jobs(
                    query=job_title,
                    location=location,
                    num_pages=2
                )
                
                if not jobs.empty:
                    st.session_state.jobs_df = jobs
                    st.success(f"✅ Found {len(jobs)} jobs!")
                else:
                    st.error("❌ No jobs found")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    st.divider()
    
    # Resume stats
    if st.session_state.resume_text:
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

# Main content
tab1, tab2 = st.tabs(["📄 Upload Resume", "🎯 Job Matches"])

# Tab 1: Upload Resume
with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📤 Upload Your Resume")
        st.markdown("<p class='gray-text'>Supported formats: PDF, DOCX</p>", unsafe_allow_html=True)
        
        # File upload
        uploaded_file = st.file_uploader("Choose your resume file", type=['pdf', 'docx'], label_visibility="collapsed")
        
        if uploaded_file:
            try:
                if uploaded_file.name.lower().endswith('.pdf'):
                    resume_text = extract_text_from_pdf(uploaded_file)
                else:
                    resume_text = extract_text_from_docx(uploaded_file)
                
                if resume_text:
                    st.session_state.resume_text = clean_text(resume_text)
                    st.success(f"✅ Resume uploaded successfully! ({uploaded_file.name})")
                    
                    # Show preview
                    with st.expander("👁️ Preview Resume Text"):
                        preview = st.session_state.resume_text[:500]
                        if len(st.session_state.resume_text) > 500:
                            preview += "..."
                        st.text(preview)
                else:
                    st.error("❌ Could not read file content")
                    
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
        
        # Text paste option
        st.markdown("---")
        st.markdown("### ✍️ Or Paste Resume Text")
        resume_text = st.text_area("Paste your resume here:", height=200, placeholder="Paste your resume text here...")
        
        if st.button("💾 Save Pasted Text", use_container_width=True):
            if resume_text and len(resume_text) > 50:
                st.session_state.resume_text = clean_text(resume_text)
                st.success("✅ Resume text saved successfully!")
            else:
                st.warning("⚠️ Please paste at least 50 characters")
    
    with col2:
        st.markdown("### ⚡ Quick Actions")
        
        if st.session_state.resume_text:
            # Find matches button
            if not st.session_state.jobs_df.empty:
                st.markdown(f"<div class='info-card'><div style='color: #34d399; font-size: 0.9rem;'>✓ Resume ready</div><div style='color: #34d399; font-size: 0.9rem;'>✓ {len(st.session_state.jobs_df)} jobs loaded</div></div>", unsafe_allow_html=True)
                
                if st.button("🤖 Match Jobs", type="primary", use_container_width=True):
                    with st.spinner("🔍 Analyzing and matching..."):
                        try:
                            matcher = JobMatcher()
                            matches = matcher.match_resume_to_jobs(
                                st.session_state.resume_text,
                                st.session_state.jobs_df,
                                top_n=15
                            )
                            st.session_state.matches_df = matches
                            st.session_state.active_tab = 1
                            st.success(f"✅ Found {len(matches)} matches!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
            else:
                st.info("ℹ️ Search for jobs first using the sidebar")
        else:
            st.info("ℹ️ Upload your resume to begin")
        
        # Help section
        st.markdown("---")
        st.markdown("### 💡 Tips")
        st.markdown("""
        <div class='info-card'>
        <div style='color: #9ca3af; font-size: 0.9rem;'>
        • Use a detailed resume<br>
        • Include keywords<br>
        • List your skills<br>
        • Mention experience
        </div>
        </div>
        """, unsafe_allow_html=True)

# Tab 2: Job Matches
with tab2:
    if st.session_state.matches_df.empty:
        st.markdown("""
        <div style='text-align: center; padding: 4rem 2rem;'>
            <div style='font-size: 4rem; margin-bottom: 1rem;'>🎯</div>
            <h2 style='color: #60a5fa; margin-bottom: 1rem;'>No Matches Yet</h2>
            <p style='color: #9ca3af; font-size: 1.1rem;'>Upload your resume and search for jobs to see matches here</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Reset active tab when viewing matches
        st.session_state.active_tab = 1
        
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
            
            # Key requirements section
            st.markdown("<div style='margin-top: 1rem;'><p style='color: #60a5fa; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.5rem;'>📋 KEY REQUIREMENTS</p></div>", unsafe_allow_html=True)
            
            bullets_html = "<ul class='job-bullets' style='margin-left: 1.5rem;'>"
            for point in key_points:
                bullets_html += f"<li>{point}</li>"
            bullets_html += "</ul>"
            st.markdown(bullets_html, unsafe_allow_html=True)
            
            # Skills section
            if skills:
                st.markdown("<div class='skills-section'>", unsafe_allow_html=True)
                st.markdown("<p style='color: #60a5fa; font-weight: 600; font-size: 0.9rem; margin-bottom: 0.8rem;'>🎯 REQUIRED SKILLS</p>", unsafe_allow_html=True)
                
                skills_html = ""
                for skill in skills:
                    skills_html += f"<span class='skill-tag'>{skill}</span>"
                st.markdown(skills_html, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Apply button
            st.markdown("<div style='margin-top: 1rem;'>", unsafe_allow_html=True)
            if apply_link and apply_link != '#':
                st.markdown(
                    f'<a href="{apply_link}" target="_blank" style="text-decoration: none;">'
                    '<button style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; padding: 0.7rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; width: 100%; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2); transition: all 0.3s;">Apply Now →</button>'
                    '</a>',
                    unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
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