import pandas as pd
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import time
from typing import List, Dict, Any, Optional
import logging
import random
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobSearchAPI:
    def __init__(self, api_key: str = None, use_mock: bool = True):
        """Initialize JobSearchAPI - uses mock data by default for testing"""
        load_dotenv()
        
        # Always use mock data for testing (set to False if you have real API key)
        self.use_mock = use_mock
        
        if not self.use_mock:
            if api_key:
                self.api_key = api_key
            else:
                self.api_key = os.getenv("RAPIDAPI_KEY") or ""
            
            if not self.api_key:
                logger.warning("No API key found, switching to mock data")
                self.use_mock = True
            else:
                self.base_url = "https://jsearch.p.rapidapi.com"
                self.headers = {
                    "X-RapidAPI-Key": self.api_key,
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
                }
        
        # Initialize mock jobs
        self.mock_jobs = self._create_mock_jobs()
        
        logger.info(f"Using {'MOCK' if self.use_mock else 'REAL'} data mode")
    
    def _create_mock_jobs(self) -> List[Dict]:
        """Create realistic mock job data for testing"""
        companies = [
            "Tech Innovations Inc.", "Data Analytics Corp", "Web Solutions Co.",
            "Cloud Systems LLC", "Startup Innovations", "Enterprise Software Ltd",
            "Digital Transformation Inc.", "AI Research Labs", "Mobile First Co.",
            "Cyber Security Solutions"
        ]
        
        locations = [
            ("Remote", "", "Worldwide"),
            ("New York", "NY", "USA"),
            ("San Francisco", "CA", "USA"),
            ("Austin", "TX", "USA"),
            ("Toronto", "ON", "Canada"),
            ("London", "", "UK"),
            ("Berlin", "", "Germany"),
            ("Singapore", "", "Singapore"),
            ("Sydney", "NSW", "Australia"),
            ("Tokyo", "", "Japan")
        ]
        
        job_templates = [
            {
                "title": "Senior Software Engineer",
                "description": """Looking for senior software engineer with 5+ years experience in Python, JavaScript, and cloud technologies. 
                Responsibilities include designing and implementing scalable systems, mentoring junior developers, and collaborating with cross-functional teams.
                Required skills: Python, AWS, Docker, Kubernetes, Microservices, CI/CD.
                Nice to have: React, TypeScript, Machine Learning basics.""",
                "skills": ["Python", "AWS", "Docker", "Kubernetes", "Microservices", "CI/CD", "JavaScript"],
                "employment_type": "FULLTIME",
                "salary_range": (120000, 160000),
                "experience": "5+ years"
            },
            {
                "title": "Data Scientist",
                "description": """Data scientist needed with experience in machine learning, statistical analysis, and Python. 
                Must be proficient with Pandas, NumPy, Scikit-learn, and SQL. Experience with big data tools a plus.
                Responsibilities include developing predictive models, analyzing large datasets, and presenting insights to stakeholders.""",
                "skills": ["Python", "Machine Learning", "Pandas", "NumPy", "SQL", "Statistics", "Data Analysis"],
                "employment_type": "FULLTIME",
                "salary_range": (110000, 140000),
                "experience": "3+ years"
            },
            {
                "title": "Frontend Developer (React)",
                "description": """Frontend developer with 3+ years React experience needed. Must know TypeScript, Redux, and modern CSS frameworks. 
                Experience with Next.js and responsive design required. Will be working on customer-facing web applications.""",
                "skills": ["React", "TypeScript", "JavaScript", "HTML/CSS", "Redux", "Next.js", "Responsive Design"],
                "employment_type": "FULLTIME",
                "salary_range": (90000, 130000),
                "experience": "3+ years"
            },
            {
                "title": "DevOps Engineer",
                "description": """DevOps engineer with AWS, Docker, and Kubernetes experience. CI/CD pipeline development required.
                Responsibilities include infrastructure as code, monitoring, and ensuring system reliability.
                Required: Terraform, Jenkins, Git, Linux, Bash scripting.""",
                "skills": ["AWS", "Docker", "Kubernetes", "CI/CD", "Terraform", "Linux", "Bash", "Jenkins"],
                "employment_type": "CONTRACTOR",
                "salary_range": (100000, 140000),
                "experience": "4+ years"
            },
            {
                "title": "Full Stack Developer",
                "description": """Full stack developer needed for fast-paced startup. Experience with Node.js, React, and MongoDB required.
                Will be involved in both frontend and backend development, database design, and API development.
                Bonus points for: GraphQL, AWS, Agile methodology.""",
                "skills": ["Node.js", "React", "MongoDB", "JavaScript", "REST API", "Express.js", "Git"],
                "employment_type": "FULLTIME",
                "salary_range": (85000, 120000),
                "experience": "2+ years"
            },
            {
                "title": "Machine Learning Engineer",
                "description": """ML Engineer to develop and deploy machine learning models. Experience with PyTorch/TensorFlow required.
                Responsibilities include data preprocessing, model training, deployment, and monitoring.
                Required: Python, ML frameworks, cloud deployment, data pipelines.""",
                "skills": ["Python", "Machine Learning", "PyTorch", "TensorFlow", "AWS", "Data Pipelines", "MLOps"],
                "employment_type": "FULLTIME",
                "salary_range": (130000, 170000),
                "experience": "4+ years"
            },
            {
                "title": "Backend Engineer (Python)",
                "description": """Backend engineer specializing in Python and API development. Experience with FastAPI/Django required.
                Responsibilities include building scalable APIs, database optimization, and system architecture.
                Required: Python, PostgreSQL, FastAPI, Docker, Redis.""",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "API Development", "System Design"],
                "employment_type": "FULLTIME",
                "salary_range": (95000, 135000),
                "experience": "3+ years"
            },
            {
                "title": "Cloud Architect",
                "description": """Cloud architect with expertise in AWS/GCP/Azure. Experience designing and implementing cloud solutions.
                Responsibilities include architecture design, cost optimization, security implementation, and team guidance.
                Required: Cloud certification, infrastructure design, security best practices.""",
                "skills": ["AWS", "Azure", "GCP", "Cloud Architecture", "Security", "Terraform", "Kubernetes"],
                "employment_type": "FULLTIME",
                "salary_range": (140000, 190000),
                "experience": "7+ years"
            },
            {
                "title": "Mobile Developer (React Native)",
                "description": """Mobile developer with React Native experience. Will work on cross-platform mobile applications.
                Responsibilities include app development, performance optimization, and collaborating with design team.
                Required: React Native, JavaScript, iOS/Android development, Redux.""",
                "skills": ["React Native", "JavaScript", "Mobile Development", "Redux", "iOS", "Android", "Firebase"],
                "employment_type": "FULLTIME",
                "salary_range": (85000, 125000),
                "experience": "2+ years"
            },
            {
                "title": "QA Automation Engineer",
                "description": """QA engineer with automation experience. Selenium, Cypress, or similar frameworks required.
                Responsibilities include test automation, CI/CD integration, and ensuring software quality.
                Required: Automation testing, Selenium, Python/Java, CI/CD, Agile.""",
                "skills": ["Automation Testing", "Selenium", "Python", "CI/CD", "Test Planning", "Agile", "Quality Assurance"],
                "employment_type": "FULLTIME",
                "salary_range": (80000, 110000),
                "experience": "3+ years"
            }
        ]
        
        mock_jobs = []
        job_id_counter = 1
        
        for _ in range(20):  # Generate 20 mock jobs
            template = random.choice(job_templates)
            company = random.choice(companies)
            location = random.choice(locations)
            
            # Add some variation to make jobs unique
            salary_min, salary_max = template["salary_range"]
            salary_min = random.randint(int(salary_min * 0.9), salary_min)
            salary_max = random.randint(salary_max, int(salary_max * 1.1))
            
            job = {
                "job_id": f"mock_{job_id_counter}_{int(time.time())}",
                "job_title": template["title"],
                "employer_name": company,
                "job_city": location[0],
                "job_state": location[1],
                "job_country": location[2],
                "job_description": template["description"],
                "job_apply_link": f"https://example.com/apply/{job_id_counter}",
                "job_is_remote": location[0] == "Remote",
                "job_employment_type": template["employment_type"],
                "job_min_salary": salary_min,
                "job_max_salary": salary_max,
                "job_salary_currency": "USD",
                "job_salary_period": "YEAR",
                "job_required_experience": {"required_experience_in_months": template["experience"]},
                "job_benefits": ["Health Insurance", "Paid Time Off", "Flexible Hours", "Remote Work Option"],
                "job_publisher": "MockJobBoard",
                "employer_logo": f"https://logo.clearbit.com/{company.lower().replace(' ', '')}.com",
                "employer_website": f"https://www.{company.lower().replace(' ', '')}.com",
                "job_highlights": {
                    "Qualifications": [f"{template['experience']} experience", "Bachelor's degree"],
                    "Responsibilities": ["Develop and maintain software", "Collaborate with team", "Write clean code"]
                }
            }
            
            mock_jobs.append(job)
            job_id_counter += 1
        
        return mock_jobs
    
    def _extract_salary_details(self, job_data: Dict) -> Dict[str, Any]:
        """Extract salary information from job data"""
        salary_info = {
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "USD",
            "salary_period": "year",
            "salary_display": "Not specified",
            "is_estimated": False
        }
        
        try:
            min_salary = job_data.get("job_min_salary")
            max_salary = job_data.get("job_max_salary")
            currency = job_data.get("job_salary_currency", "USD")
            period = job_data.get("job_salary_period", "YEAR").lower()
            
            if min_salary and max_salary:
                salary_info["salary_min"] = float(min_salary)
                salary_info["salary_max"] = float(max_salary)
                salary_info["salary_currency"] = currency
                salary_info["salary_period"] = period
                
                if period == "year":
                    display_min = f"${salary_info['salary_min']:,.0f}"
                    display_max = f"${salary_info['salary_max']:,.0f}"
                    salary_info["salary_display"] = f"{display_min} - {display_max}/year"
                elif period == "hour":
                    display_min = f"${salary_info['salary_min']:.2f}"
                    display_max = f"${salary_info['salary_max']:.2f}"
                    salary_info["salary_display"] = f"{display_min} - {display_max}/hour"
        
        except Exception as e:
            logger.debug(f"Error extracting salary: {e}")
        
        return salary_info
    
    def _extract_skills(self, description: str, title: str) -> List[str]:
        """Extract skills from job description and title"""
        if not description:
            description = ""
        if not title:
            title = ""
        
        skills = set()
        text = f"{title} {description}".upper()
        
        # Common skill patterns
        skill_patterns = [
            r'\b(?:Python|Java|JavaScript|TypeScript|C\+\+|C#|Ruby|Go|Rust|Swift|Kotlin|PHP|Scala|Perl|R)\b',
            r'\b(?:React(?:\.js|JS)?|Angular|Vue(?:\.js)?|Next\.js|Node(?:\.js)?|Django|Flask|Spring|Express|FastAPI|Laravel)\b',
            r'\b(?:AWS|Amazon Web Services|Azure|GCP|Google Cloud)\b',
            r'\b(?:Docker|Kubernetes|k8s|Jenkins|GitLab|GitHub Actions|CircleCI|TravisCI|Ansible|Terraform)\b',
            r'\b(?:SQL|PostgreSQL|MySQL|MongoDB|Redis|Oracle|Cassandra|DynamoDB|SQL Server|MariaDB|Firebase)\b',
            r'\b(?:Machine Learning|ML|AI|Artificial Intelligence|Data Science|Analytics|Statistics|Deep Learning|NLP|Computer Vision)\b',
            r'\b(?:TensorFlow|PyTorch|Scikit-learn|Keras|Pandas|NumPy|SciPy|Matplotlib|Seaborn|Jupyter)\b',
            r'\b(?:HTML5|CSS3|Sass|SCSS|Less|Tailwind CSS|Bootstrap|Material-UI|Chakra UI|Webpack|Babel)\b',
            r'\b(?:Agile|Scrum|Kanban|DevOps|CI/CD|TDD|BDD|Microservices|REST|GraphQL|SOAP|OOP)\b',
            r'\b(?:Git|GitHub|GitLab|Jira|Confluence|Slack|Figma|Adobe Creative Suite|Tableau|Power BI|Excel)\b'
        ]
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = match.strip()
                if skill.lower() in ['sql', 'ml', 'ai', 'api', 'oop', 'ci/cd']:
                    skill = skill.upper()
                else:
                    skill = skill.title()
                skills.add(skill)
        
        return sorted(list(skills))[:15]
    
    def _extract_remote_status(self, job_data: Dict) -> Dict[str, Any]:
        """Extract remote work status"""
        remote_info = {
            "is_remote": False,
            "is_hybrid": False,
            "is_onsite": True,
            "remote_type": "On-site"
        }
        
        if job_data.get("job_is_remote"):
            remote_info["is_remote"] = True
            remote_info["is_onsite"] = False
            remote_info["remote_type"] = "Remote"
        
        text = f"{job_data.get('job_title', '')} {job_data.get('job_description', '')}".lower()
        
        if 'remote' in text:
            remote_info["is_remote"] = True
            remote_info["remote_type"] = "Remote"
        elif 'hybrid' in text:
            remote_info["is_hybrid"] = True
            remote_info["remote_type"] = "Hybrid"
        
        return remote_info
    
    def _enhance_job_data(self, job_data: Dict) -> Dict[str, Any]:
        """Enhance job data with extracted information"""
        # Extract basic info
        job_id = job_data.get("job_id", "")
        job_title = job_data.get("job_title", "Not specified")
        employer_name = job_data.get("employer_name", "Not specified")
        
        # Location
        city = str(job_data.get("job_city", ""))
        state = str(job_data.get("job_state", ""))
        country = str(job_data.get("job_country", ""))
        
        location_parts = []
        if city:
            location_parts.append(city)
        if state and state != city:
            location_parts.append(state)
        if country and country not in location_parts:
            if len(country) > 2:
                location_parts.append(country)
        
        location_display = ", ".join(location_parts) if location_parts else "Location not specified"
        
        # Extract enhanced information
        salary_info = self._extract_salary_details(job_data)
        remote_info = self._extract_remote_status(job_data)
        
        # Description
        job_description = job_data.get("job_description", "")
        if job_description and len(job_description) > 2000:
            job_description = job_description[:2000] + "..."
        
        # Skills
        skills = self._extract_skills(job_description, job_title)
        
        # Employment type
        emp_type = job_data.get("job_employment_type", "")
        if emp_type == "FULLTIME":
            employment_type = "Full-time"
        elif emp_type == "PARTTIME":
            employment_type = "Part-time"
        elif emp_type == "CONTRACTOR":
            employment_type = "Contract"
        elif emp_type == "INTERN":
            employment_type = "Internship"
        else:
            employment_type = "Full-time"
        
        # Experience
        exp_data = job_data.get("job_required_experience", {})
        if isinstance(exp_data, dict):
            experience_level = exp_data.get("required_experience_in_months", "Not specified")
        else:
            experience_level = str(exp_data)
        
        # Posting date
        posting_timestamp = job_data.get("job_posted_at_timestamp")
        if posting_timestamp:
            try:
                posting_date = datetime.fromtimestamp(posting_timestamp).strftime("%Y-%m-%d")
                posting_display = posting_date
            except:
                posting_display = "Recent"
        else:
            posting_display = "Recent"
        
        # Build enhanced job
        enhanced_job = {
            "job_id": job_id,
            "job_title": job_title,
            "employer_name": employer_name,
            "job_city": city,
            "job_state": state,
            "job_country": country,
            "location_display": location_display,
            "salary_min": salary_info["salary_min"],
            "salary_max": salary_info["salary_max"],
            "salary_currency": salary_info["salary_currency"],
            "salary_period": salary_info["salary_period"],
            "salary_display": salary_info["salary_display"],
            "is_remote": remote_info["is_remote"],
            "is_hybrid": remote_info["is_hybrid"],
            "remote_type": remote_info["remote_type"],
            "employment_type": employment_type,
            "experience_level": experience_level,
            "job_description": job_description,
            "company_name": employer_name,
            "company_website": job_data.get("employer_website", ""),
            "company_logo": job_data.get("employer_logo", ""),
            "job_apply_link": job_data.get("job_apply_link", "#"),
            "skills": json.dumps(skills),
            "skills_count": len(skills),
            "posting_date": posting_display,
            "posting_timestamp": posting_timestamp,
            "benefits": ", ".join(job_data.get("job_benefits", [])),
            "job_publisher": job_data.get("job_publisher", ""),
            "description_length": len(job_description),
            "has_salary": salary_info["salary_display"] != "Not specified",
            "has_apply_link": bool(job_data.get("job_apply_link"))
        }
        
        return enhanced_job
    
    def search_jobs(self, query: str, location: str = "", num_pages: int = 1, 
                   employment_types: List[str] = None, date_posted: str = "all",
                   remote_only: bool = False) -> pd.DataFrame:
        """Search for jobs - uses mock data for testing"""
        logger.info(f"Searching for '{query}' in {location} (mock data)")
        
        # Filter mock jobs based on query
        filtered_jobs = []
        query_lower = query.lower() if query else ""
        
        for job in self.mock_jobs:
            include_job = True
            
            # Filter by query
            if query_lower:
                job_text = f"{job['job_title']} {job['job_description']}".lower()
                if query_lower not in job_text:
                    continue
            
            # Filter by location
            if location:
                location_lower = location.lower()
                if location_lower == "remote":
                    if not job.get("job_is_remote", False):
                        continue
                elif location_lower not in f"{job['job_city']} {job['job_country']}".lower():
                    # For testing, include some jobs even if location doesn't match exactly
                    if random.random() > 0.3:  # 70% chance to exclude
                        continue
            
            # Filter by remote only
            if remote_only and not job.get("job_is_remote", False):
                continue
            
            filtered_jobs.append(job)
        
        # If no filtered jobs, use all mock jobs
        if not filtered_jobs:
            filtered_jobs = self.mock_jobs[:10]
        
        # Enhance job data
        enhanced_jobs = []
        for job in filtered_jobs[:15]:  # Limit to 15 jobs
            try:
                enhanced_job = self._enhance_job_data(job)
                enhanced_jobs.append(enhanced_job)
            except Exception as e:
                logger.warning(f"Error enhancing job: {e}")
                continue
        
        df = pd.DataFrame(enhanced_jobs)
        logger.info(f"✅ Found {len(df)} mock jobs")
        return df
    
    def get_job_details(self, job_id: str) -> Optional[Dict]:
        """Get details for specific job (mock)"""
        for job in self.mock_jobs:
            if job.get("job_id") == job_id:
                return self._enhance_job_data(job)
        return None

# Simple wrapper for backward compatibility
def search_jobs_simple(query: str, location: str, num_pages: int = 2) -> pd.DataFrame:
    """Simple wrapper for backward compatibility"""
    api = JobSearchAPI(use_mock=True)
    return api.search_jobs(query, location, num_pages)

# Test function
def test_api():
    """Test the API functionality"""
    print("🧪 Testing JobSearchAPI (Mock Mode)...")
    
    api = JobSearchAPI(use_mock=True)
    
    # Test search
    print("\n1. Searching for 'software engineer' jobs...")
    jobs = api.search_jobs("software engineer", "Remote", num_pages=1)
    
    if not jobs.empty:
        print(f"✅ Found {len(jobs)} mock jobs")
        print(f"   Sample job: {jobs.iloc[0]['job_title']} at {jobs.iloc[0]['employer_name']}")
        print(f"   Salary: {jobs.iloc[0]['salary_display']}")
        print(f"   Remote: {jobs.iloc[0]['remote_type']}")
        
        # Test skills extraction
        skills = json.loads(jobs.iloc[0]['skills'])
        print(f"   Skills: {', '.join(skills[:5])}")
    else:
        print("❌ No jobs found")
    
    print("\n🧪 Test completed!")

if __name__ == "__main__":
    test_api()