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
    page_title="HirePilot.",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "HirePilot: AI-Powered Job Search"
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
</div>

<script>
(function() {
    'use strict';
    
    // Track which steps have been scrolled to avoid duplicate scrolling
    const scrolledSteps = new Set();
    let isUserScrolling = false;
    let scrollTimeout = null;
    let lastScrollCheck = 0;
    
    // Detect user-initiated scrolling
    let lastScrollTop = window.pageYOffset || document.documentElement.scrollTop;
    let scrollDetectionTimeout = null;
    
    window.addEventListener('scroll', function() {
        const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
        const scrollDelta = Math.abs(currentScroll - lastScrollTop);
        
        if (scrollDelta > 10) {
            isUserScrolling = true;
            clearTimeout(scrollDetectionTimeout);
            scrollDetectionTimeout = setTimeout(function() {
                isUserScrolling = false;
            }, 2000);
        }
        lastScrollTop = currentScroll;
    }, { passive: true });
    
    // Smooth scroll to element with fade-in animation
    function smoothScrollToStep(stepElement, delay = 300) {
        if (!stepElement || scrolledSteps.has(stepElement.id)) {
            return;
        }
        
        // Wait for layout to stabilize
        setTimeout(function() {
            if (isUserScrolling) {
                // User is manually scrolling, don't interfere
                return;
            }
            
            // Check if element is in viewport (top 40% of screen)
            const rect = stepElement.getBoundingClientRect();
            const viewportTop = window.innerHeight * 0.1;
            const isVisible = rect.top >= viewportTop && rect.top < window.innerHeight * 0.4;
            
            if (!isVisible && rect.top > 0) {
                // Add fade-in class before scrolling
                stepElement.classList.add('step-entering');
                
                // Calculate scroll position with offset
                const elementTop = stepElement.offsetTop;
                const offset = 80; // Offset from top
                
                // Smooth scroll
                window.scrollTo({
                    top: elementTop - offset,
                    behavior: 'smooth'
                });
                
                // Mark as scrolled
                scrolledSteps.add(stepElement.id);
            } else if (isVisible) {
                // Already visible, just add animation
                stepElement.classList.add('step-entering');
                scrolledSteps.add(stepElement.id);
            }
        }, delay);
    }
    
    // Check step completion and scroll
    function checkAndScrollSteps() {
        const now = Date.now();
        if (now - lastScrollCheck < 500) {
            return; // Throttle checks
        }
        lastScrollCheck = now;
        
        // Step 1: Check if resume is uploaded
        const step1Complete = document.querySelector('[data-step-complete="1"]');
        const step1Header = document.getElementById('step-1-header');
        if (step1Header && step1Complete && !scrolledSteps.has('step-1-header')) {
            smoothScrollToStep(step1Header, 600);
            return; // Only scroll to one step at a time
        }
        
        // Step 2: Check if search is complete
        const step2Complete = document.querySelector('[data-step-complete="2"]');
        const step2Header = document.getElementById('step-2-header');
        if (step2Header && step2Complete && !scrolledSteps.has('step-2-header')) {
            // Only scroll if Step 1 was already scrolled or completed
            if (scrolledSteps.has('step-1-header') || step1Complete) {
                smoothScrollToStep(step2Header, 400);
                return;
            }
        }
        
        // Step 3: Check if results are visible
        const step3Complete = document.querySelector('[data-step-complete="3"]');
        const step3Header = document.getElementById('step-3-header');
        if (step3Header && step3Complete && !scrolledSteps.has('step-3-header')) {
            // Only scroll if Step 2 was already scrolled or completed
            if (scrolledSteps.has('step-2-header') || step2Complete) {
                smoothScrollToStep(step3Header, 400);
            }
        }
    }
    
    // Use MutationObserver to detect when steps are added/updated
    let observer = null;
    
    function init() {
        // Observe the main content area for Streamlit
        const mainContent = document.querySelector('[data-testid="stAppViewContainer"]') || 
                          document.querySelector('.main') || 
                          document.body;
        
        if (mainContent && !observer) {
            observer = new MutationObserver(function(mutations) {
                let shouldCheck = false;
                mutations.forEach(function(mutation) {
                    if (mutation.addedNodes.length > 0) {
                        // Check if any added node is a step element
                        for (let node of mutation.addedNodes) {
                            if (node.nodeType === 1) {
                                if (node.id && node.id.startsWith('step-')) {
                                    shouldCheck = true;
                                    break;
                                }
                                if (node.querySelector && node.querySelector('[id^="step-"]')) {
                                    shouldCheck = true;
                                    break;
                                }
                            }
                        }
                    }
                    if (mutation.type === 'attributes' && 
                        (mutation.attributeName === 'aria-expanded' || mutation.attributeName === 'class')) {
                        shouldCheck = true;
                    }
                });
                
                if (shouldCheck) {
                    // Debounce checks
                    clearTimeout(window.scrollCheckTimeout);
                    window.scrollCheckTimeout = setTimeout(checkAndScrollSteps, 300);
                }
            });
            
            observer.observe(mainContent, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['aria-expanded', 'class', 'id']
            });
        }
        
        // Initial check after page load
        setTimeout(checkAndScrollSteps, 1000);
        
        // Periodic check for dynamic content (less frequent)
        setInterval(checkAndScrollSteps, 1500);
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM already ready
        setTimeout(init, 100);
    }
    
    // Re-initialize on Streamlit reruns
    if (window.parent !== window) {
        // Running in iframe (Streamlit)
        window.addEventListener('load', init);
    }
})();
</script>
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
    
    st.success(f"🎉 Found {len(st.session_state.matches_df)} jobs matching your resume!")

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
