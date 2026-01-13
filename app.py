import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import tempfile
from datetime import datetime

# Import our modules
from job_api import JobSearchAPI
from job_matcher_simple import JobMatcher
from resume_parser_simple import extract_text_from_pdf, extract_text_from_docx

# Set page config
st.set_page_config(
    page_title="AI Resume Matcher - Real Jobs",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize API and matcher
@st.cache_resource
def get_job_api():
    return JobSearchAPI()

@st.cache_resource
def get_job_matcher():
    return JobMatcher()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
    }
    .job-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        color: white;
    }
    .match-score {
        font-size: 1.5rem;
        font-weight: bold;
        text-align: center;
    }
    .high-match { color: #10B981; }
    .medium-match { color: #F59E0B; }
    .low-match { color: #EF4444; }
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown('<h1 class="main-header">🤖 AI Resume Matcher with Real Jobs</h1>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'resume_text' not in st.session_state:
        st.session_state.resume_text = ""
    if 'matches' not in st.session_state:
        st.session_state.matches = pd.DataFrame()
    if 'jobs_df' not in st.session_state:
        st.session_state.jobs_df = pd.DataFrame()
    if 'search_query' not in st.session_state:
        st.session_state.search_query = "software engineer"
    if 'search_location' not in st.session_state:
        st.session_state.search_location = "United States"
    
    # Sidebar for job search
    with st.sidebar:
        st.header("🔍 Job Search Parameters")
        
        st.session_state.search_query = st.text_input(
            "Job Title/Keywords",
            value=st.session_state.search_query,
            help="e.g., software engineer, data scientist, product manager"
        )
        
        st.session_state.search_location = st.text_input(
            "Location",
            value=st.session_state.search_location,
            help="e.g., San Francisco, Remote, United States"
        )
        
        num_pages = st.slider("Number of job pages", 1, 5, 1, 
                            help="More pages = more jobs (slower)")
        
        if st.button("🔎 Search Jobs", type="primary", use_container_width=True):
            with st.spinner("Fetching real jobs from API..."):
                api = get_job_api()
                jobs_df = api.search_jobs(
                    query=st.session_state.search_query,
                    location=st.session_state.search_location,
                    num_pages=num_pages
                )
                
                if not jobs_df.empty:
                    st.session_state.jobs_df = jobs_df
                    st.success(f"Found {len(jobs_df)} jobs!")
                else:
                    st.error("No jobs found. Try different keywords.")
        
        st.divider()
        
        # Show API status
        st.header("⚙️ API Status")
        api_key = os.getenv("RAPIDAPI_KEY") or (st.secrets.get("RAPIDAPI_KEY") if hasattr(st, 'secrets') else None)
        if api_key:
            st.success("✅ API Key Configured")
        else:
            st.warning("⚠️ API Key Missing")
            st.info("Set RAPIDAPI_KEY in Hugging Face secrets")
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📤 Upload Resume", "🎯 Job Matches", "📊 Analytics"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.header("Upload Your Resume")
            uploaded_file = st.file_uploader(
                "Choose PDF or DOCX file",
                type=['pdf', 'docx'],
                help="Upload your resume for analysis"
            )
            
            if uploaded_file:
                # Save and parse the file
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    # Parse based on file type
                    if uploaded_file.name.lower().endswith('.pdf'):
                        resume_text = extract_text_from_pdf(tmp_path)
                    else:
                        resume_text = extract_text_from_docx(tmp_path)
                    
                    # Clean up
                    os.unlink(tmp_path)
                    
                    # Store in session state
                    st.session_state.resume_text = resume_text
                    
                    st.success(f"✅ Resume parsed successfully! ({len(resume_text)} characters)")
                    
                    # Show extracted text
                    with st.expander("📝 View Parsed Text"):
                        st.text_area("Extracted Text", resume_text[:1500] + "..." if len(resume_text) > 1500 else resume_text, 
                                   height=300)
                    
                    # Extract keywords
                    if resume_text:
                        matcher = get_job_matcher()
                        keywords = matcher.extract_keywords(resume_text)
                        
                        st.subheader("🔑 Extracted Keywords")
                        cols = st.columns(4)
                        for i, keyword in enumerate(keywords[:12]):
                            with cols[i % 4]:
                                st.markdown(f"`{keyword}`")
                    
                    # Match button
                    if not st.session_state.jobs_df.empty:
                        if st.button("🤖 Find Matching Jobs", type="primary", use_container_width=True):
                            with st.spinner("Analyzing resume and matching with jobs..."):
                                matcher = get_job_matcher()
                                matches = matcher.match_resume_to_jobs(
                                    resume_text, 
                                    st.session_state.jobs_df,
                                    top_n=10
                                )
                                st.session_state.matches = matches
                                st.rerun()
                    else:
                        st.warning("Search for jobs first using the sidebar!")
                        
                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
        
        with col2:
            st.header("💡 How It Works")
            st.info("""
            1. **Search** for jobs using sidebar
            2. **Upload** your resume (PDF/DOCX)
            3. **AI analyzes** your skills & experience
            4. **Get matches** with real job listings
            5. **Apply** directly to matched jobs
            
            **Features:**
            - Real-time job search
            - Skill-based matching
            - Salary insights
            - Direct apply links
            """)
            
            # Stats if we have jobs
            if not st.session_state.jobs_df.empty:
                st.metric("Available Jobs", len(st.session_state.jobs_df))
                
                # Top locations
                if 'location' in st.session_state.jobs_df.columns:
                    top_locations = st.session_state.jobs_df['location'].value_counts().head(3)
                    st.write("**Top Locations:**")
                    for loc, count in top_locations.items():
                        st.write(f"- {loc}: {count}")
    
    with tab2:
        st.header("🎯 Your Job Matches")
        
        if st.session_state.matches.empty:
            st.info("👈 Upload a resume and search for jobs to see matches!")
            
            # Show available jobs if any
            if not st.session_state.jobs_df.empty:
                st.subheader("📋 Available Jobs Preview")
                preview_df = st.session_state.jobs_df[['job_title', 'company', 'location', 'employment_type']].head(5)
                st.dataframe(preview_df, use_container_width=True)
        else:
            # Display matches
            st.success(f"Found {len(st.session_state.matches)} matching jobs!")
            
            for idx, row in st.session_state.matches.iterrows():
                match_score = row['match_score']
                
                # Determine color based on score
                if match_score >= 70:
                    score_color = "high-match"
                    badge = "🔥 Excellent Match"
                elif match_score >= 40:
                    score_color = "medium-match"
                    badge = "👍 Good Match"
                else:
                    score_color = "low-match"
                    badge = "📊 Fair Match"
                
                # Create job card
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"### {row['job_title']}")
                        st.markdown(f"**Company:** {row['company']}")
                        st.markdown(f"**Location:** {row['location']}")
                        st.markdown(f"**Type:** {row['employment_type']}")
                        
                        if row['salary'] and row['salary'] != "Not specified":
                            st.markdown(f"**Salary:** {row['salary']}")
                        
                        # Skills
                        if row['skills']:
                            skills_text = ", ".join(row['skills'][:5])
                            st.markdown(f"**Skills:** {skills_text}")
                    
                    with col2:
                        st.markdown(f'<div class="match-score {score_color}">{match_score:.0f}%</div>', 
                                  unsafe_allow_html=True)
                        st.caption(badge)
                        
                        # Progress bar
                        st.progress(match_score / 100)
                    
                    with col3:
                        if row['apply_link']:
                            st.link_button("📨 Apply Now", row['apply_link'])
                        else:
                            st.button("🔍 View Details", key=f"view_{idx}")
                        
                        # Remote badge
                        if row.get('remote'):
                            st.markdown("🏠 **Remote**")
                    
                    # Job description preview
                    with st.expander("View Job Description & Details"):
                        col_a, col_b = st.columns([2, 1])
                        
                        with col_a:
                            st.write(row['description'][:500] + "..." if len(row['description']) > 500 else row['description'])
                        
                        with col_b:
                            # Match breakdown
                            st.write("**Match Breakdown:**")
                            st.write(f"• Content Match: {row.get('tfidf_score', 0):.0f}%")
                            st.write(f"• Skills Match: {row.get('skill_score', 0):.0f}%")
                            
                            # Skills comparison
                            if row['skills']:
                                st.write("**Required Skills:**")
                                for skill in row['skills'][:5]:
                                    st.write(f"- {skill}")
                        
                        # Apply button at bottom
                        if row['apply_link']:
                            st.link_button("👉 Apply for this Position", row['apply_link'], 
                                         use_container_width=True)
                    
                    st.divider()
    
    with tab3:
        st.header("📊 Analytics Dashboard")
        
        if st.session_state.matches.empty:
            st.info("No matches to analyze yet. Get some matches first!")
        else:
            # Create analytics
            matches_df = st.session_state.matches
            
            # 1. Score distribution
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Match Score Distribution")
                fig1 = px.histogram(matches_df, x='match_score', nbins=10,
                                  title="Distribution of Match Scores",
                                  color_discrete_sequence=['#6366F1'])
                fig1.update_layout(showlegend=False)
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                st.subheader("Top Skills in Matches")
                # Flatten skills list
                all_skills = []
                for skills in matches_df['skills']:
                    if isinstance(skills, list):
                        all_skills.extend(skills)
                
                if all_skills:
                    skills_series = pd.Series(all_skills).value_counts().head(10)
                    fig2 = px.bar(x=skills_series.values, y=skills_series.index,
                                orientation='h', title="Most Required Skills",
                                color=skills_series.values,
                                color_continuous_scale='Blues')
                    fig2.update_layout(yaxis_title="Skills", showlegend=False)
                    st.plotly_chart(fig2, use_container_width=True)
            
            # 2. Salary vs Match Score (if available)
            st.subheader("Job Insights")
            
            # Try to extract numeric salary
            def extract_avg_salary(salary_str):
                if isinstance(salary_str, str) and salary_str != "Not specified":
                    numbers = re.findall(r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)', salary_str)
                    if numbers:
                        # Convert to numbers and average
                        nums = [float(num.replace(',', '')) for num in numbers]
                        return sum(nums) / len(nums)
                return None
            
            matches_df['salary_num'] = matches_df['salary'].apply(extract_avg_salary)
            valid_salaries = matches_df.dropna(subset=['salary_num'])
            
            if not valid_salaries.empty:
                fig3 = px.scatter(valid_salaries, x='salary_num', y='match_score',
                                size='match_score', color='match_score',
                                hover_data=['job_title', 'company', 'location'],
                                title="Salary vs Match Score",
                                color_continuous_scale='Viridis')
                fig3.update_layout(xaxis_title="Estimated Salary ($)")
                st.plotly_chart(fig3, use_container_width=True)
            
            # 3. Location heatmap
            if 'location' in matches_df.columns:
                st.subheader("Job Locations")
                location_counts = matches_df['location'].value_counts().reset_index()
                location_counts.columns = ['Location', 'Count']
                
                fig4 = px.treemap(location_counts, path=['Location'], values='Count',
                                title="Jobs by Location",
                                color='Count', color_continuous_scale='RdBu')
                st.plotly_chart(fig4, use_container_width=True)

if __name__ == "__main__":
    main()