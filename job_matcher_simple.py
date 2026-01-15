import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import List, Dict, Any, Optional, Tuple
import json
from collections import Counter
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobMatcher:
    def __init__(self, use_weighted_matching: bool = True, use_skill_extraction: bool = True):
        """
        Initialize Job Matcher with enhanced capabilities
        
        Args:
            use_weighted_matching: Whether to use weighted matching (skills 40%, title 30%, description 20%, company 10%)
            use_skill_extraction: Whether to extract and match skills separately
        """
        self.use_weighted_matching = use_weighted_matching
        self.use_skill_extraction = use_skill_extraction
        
        # Different vectorizers for different text types
        self.title_vectorizer = TfidfVectorizer(
            stop_words='english', 
            max_features=500,
            ngram_range=(1, 2)
        )
        
        self.description_vectorizer = TfidfVectorizer(
            stop_words='english', 
            max_features=1000,
            ngram_range=(1, 3)
        )
        
        self.skill_vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=300
        )
        
        # Predefined skill categories and weights
        self.skill_categories = {
            'technical': 1.2,      # Programming languages, frameworks, tools
            'soft': 1.0,           # Communication, leadership, teamwork
            'domain': 1.1,         # Industry-specific knowledge
            'certifications': 1.3  # Certifications and education
        }
        
        # Common skills dictionary for better matching
        self.skill_synonyms = {
            'python': ['python', 'python3', 'python programming'],
            'javascript': ['javascript', 'js', 'ecmascript'],
            'react': ['react', 'react.js', 'reactjs'],
            'aws': ['aws', 'amazon web services'],
            'docker': ['docker', 'containerization'],
            'kubernetes': ['kubernetes', 'k8s'],
            'sql': ['sql', 'structured query language'],
            'mongodb': ['mongodb', 'mongo'],
            'postgresql': ['postgresql', 'postgres'],
            'git': ['git', 'version control'],
            'agile': ['agile', 'scrum', 'kanban'],
            'ci/cd': ['ci/cd', 'continuous integration', 'continuous deployment'],
            'rest': ['rest', 'restful', 'rest api'],
            'graphql': ['graphql', 'graph ql']
        }
    
    def extract_resume_skills(self, resume_text: str) -> List[str]:
        """Extract skills from resume text"""
        if not resume_text:
            return []
        
        # Common skill patterns
        skill_patterns = [
            # Programming languages
            r'\b(?:Python|Java|JavaScript|TypeScript|C\+\+|C#|Ruby|Go|Rust|Swift|Kotlin|PHP|Scala|Perl|R)\b',
            # Frameworks
            r'\b(?:React(?:\.js|JS)?|Angular|Vue(?:\.js)?|Next\.js|Node(?:\.js)?|Django|Flask|Spring|Express|FastAPI|Laravel)\b',
            # Cloud & DevOps
            r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|Git|CI/CD|Terraform|Ansible|GitLab|GitHub Actions)\b',
            # Databases
            r'\b(?:SQL|PostgreSQL|MySQL|MongoDB|Redis|Oracle|Cassandra|DynamoDB|SQL Server|MariaDB)\b',
            # Data Science & ML
            r'\b(?:Machine Learning|ML|AI|Data Science|Analytics|Statistics|Deep Learning|TensorFlow|PyTorch|Pandas|NumPy)\b',
            # Web Technologies
            r'\b(?:HTML5|CSS3|Sass|SCSS|Tailwind CSS|Bootstrap|Material-UI|Webpack|Babel)\b',
            # Methodologies
            r'\b(?:Agile|Scrum|Kanban|DevOps|TDD|BDD|Microservices|REST|GraphQL|API|OOP)\b',
            # Tools
            r'\b(?:GitHub|GitLab|Jira|Confluence|Slack|Figma|Adobe Creative Suite|Tableau|Power BI|Excel)\b',
        ]
        
        skills = set()
        resume_upper = resume_text.upper()
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, resume_text, re.IGNORECASE)
            for match in matches:
                # Standardize skill names
                skill = match.strip()
                if skill.lower() in ['sql', 'ml', 'ai', 'api', 'oop', 'ci/cd']:
                    skill = skill.upper()
                else:
                    skill = skill.title()
                skills.add(skill)
        
        # Extract from experience sections
        lines = resume_text.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['experience with', 'proficient in', 'skilled in', 'knowledge of']):
                words = re.findall(r'\b[A-Za-z][A-Za-z0-9+]*\b', line)
                for word in words:
                    if len(word) > 2 and word.lower() not in ['the', 'and', 'with', 'using']:
                        skills.add(word.title())
        
        return sorted(list(skills))
    
    def extract_job_skills(self, job_data: Dict) -> List[str]:
        """Extract skills from job data"""
        if 'skills' in job_data and job_data['skills']:
            try:
                skills_json = job_data['skills']
                if isinstance(skills_json, str):
                    return json.loads(skills_json)
                elif isinstance(skills_json, list):
                    return skills_json
            except:
                pass
        
        # Fallback: extract from description
        description = job_data.get('job_description', '') + ' ' + job_data.get('job_title', '')
        return self.extract_resume_skills(description)
    
    def calculate_skill_match(self, resume_skills: List[str], job_skills: List[str]) -> float:
        """Calculate skill matching score (0-100)"""
        if not resume_skills or not job_skills:
            return 0.0
        
        # Normalize skills to lowercase for comparison
        resume_skills_lower = [skill.lower() for skill in resume_skills]
        job_skills_lower = [skill.lower() for skill in job_skills]
        
        # Check exact matches
        matched_skills = set(resume_skills_lower) & set(job_skills_lower)
        
        # Check partial matches using synonyms
        for resume_skill in resume_skills_lower:
            for job_skill in job_skills_lower:
                # Check if they're synonyms
                if self._are_skills_synonyms(resume_skill, job_skill):
                    matched_skills.add(resume_skill)
                    matched_skills.add(job_skill)
        
        # Calculate score
        if not job_skills_lower:
            return 0.0
        
        match_percentage = (len(matched_skills) / len(job_skills_lower)) * 100
        return min(match_percentage, 100)
    
    def _are_skills_synonyms(self, skill1: str, skill2: str) -> bool:
        """Check if two skills are synonyms"""
        skill1_lower = skill1.lower()
        skill2_lower = skill2.lower()
        
        # Direct match
        if skill1_lower == skill2_lower:
            return True
        
        # Check synonyms dictionary
        for synonyms in self.skill_synonyms.values():
            if skill1_lower in synonyms and skill2_lower in synonyms:
                return True
        
        # Check if one contains the other
        if skill1_lower in skill2_lower or skill2_lower in skill1_lower:
            return len(skill1_lower) > 3 and len(skill2_lower) > 3  # Avoid short word matches
        
        return False
    
    def calculate_title_match(self, resume_text: str, job_title: str) -> float:
        """Calculate title matching score"""
        if not job_title or not resume_text:
            return 0.0
        
        # Common title keywords and their weights
        title_keywords = {
            'senior': 1.3,
            'lead': 1.4,
            'principal': 1.5,
            'junior': 0.8,
            'entry': 0.7,
            'associate': 0.9,
            'intern': 0.6,
            'manager': 1.2,
            'director': 1.4,
            'vp': 1.5,
            'cto': 1.6
        }
        
        # Check if resume mentions similar level
        resume_lower = resume_text.lower()
        job_lower = job_title.lower()
        
        base_score = 0.0
        
        # Check for exact title matches
        title_words = job_lower.split()
        for word in title_words:
            if len(word) > 3 and word in resume_lower:
                base_score += 10
        
        # Check for title level matches
        for keyword, weight in title_keywords.items():
            if keyword in job_lower:
                # Check if resume mentions similar level
                level_keywords = ['senior', 'lead', 'principal', 'experienced', 'expert']
                if any(level in resume_lower for level in level_keywords):
                    base_score += 20 * weight
        
        return min(base_score, 100)
    
    def calculate_experience_match(self, resume_text: str, job_experience: str) -> float:
        """Calculate experience requirement match"""
        if not job_experience:
            return 50.0  # Default if no experience requirement specified
        
        # Extract years from experience string
        years_pattern = r'(\d+)\+?\s*(?:year|yr|years)'
        years_match = re.search(years_pattern, job_experience.lower())
        
        if not years_match:
            return 50.0
        
        required_years = int(years_match.group(1))
        
        # Try to extract experience from resume
        resume_experience_patterns = [
            r'(\d+)\+?\s*(?:year|yr|years?)\s*(?:of\s+)?experience',
            r'experience\s+(?:of\s+)?(\d+)\+?\s*(?:year|yr|years?)',
            r'(\d+)\s*(?:year|yr|years?)\s+in'
        ]
        
        resume_years = 0
        for pattern in resume_experience_patterns:
            match = re.search(pattern, resume_text.lower())
            if match:
                resume_years = int(match.group(1))
                break
        
        # If no explicit years found, estimate from job history
        if resume_years == 0:
            # Count job entries (simplified)
            job_entries = resume_text.lower().count('experience') + resume_text.lower().count('worked at')
            resume_years = min(job_entries * 2, 10)  # Estimate 2 years per job
        
        # Calculate match score
        if resume_years >= required_years:
            return 100.0
        else:
            return (resume_years / required_years) * 100
    
    def calculate_location_match(self, resume_text: str, job_location: str, is_remote: bool) -> float:
        """Calculate location compatibility score"""
        if is_remote:
            return 100.0  # Remote jobs are always location-compatible
        
        if not job_location or job_location.lower() in ['remote', 'anywhere']:
            return 100.0
        
        # Check if resume mentions location preferences
        resume_lower = resume_text.lower()
        
        # Common location keywords
        location_keywords = ['relocate', 'relocation', 'remote', 'work from home', 'wfh', 'anywhere', 'open to']
        
        # If resume mentions openness to relocation
        if any(keyword in resume_lower for keyword in location_keywords):
            return 75.0
        
        # Try to extract location from resume
        resume_location = None
        location_patterns = [
            r'location\s*:\s*([^\n]+)',
            r'based in\s+([^\n,]+)',
            r'located in\s+([^\n,]+)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, resume_lower)
            if match:
                resume_location = match.group(1).strip()
                break
        
        # If no specific location in resume, give moderate score
        if not resume_location:
            return 60.0
        
        # Simple location matching (could be enhanced with geocoding)
        job_loc_lower = job_location.lower()
        if any(term in job_loc_lower for term in ['united states', 'usa', 'us', 'america']):
            if any(term in resume_location.lower() for term in ['united states', 'usa', 'us', 'america']):
                return 90.0
            else:
                return 40.0
        
        # Check if same country/region mentioned
        if resume_location.lower() in job_loc_lower or job_loc_lower in resume_location.lower():
            return 95.0
        
        return 50.0
    
    def calculate_weighted_match_score(self, 
                                     resume_text: str, 
                                     job_data: Dict, 
                                     weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate weighted match score using multiple factors"""
        
        if weights is None:
            weights = {
                'skills': 0.40,
                'title': 0.20,
                'description': 0.25,
                'experience': 0.10,
                'location': 0.05
            }
        
        # Extract job skills
        job_skills = self.extract_job_skills(job_data)
        resume_skills = self.extract_resume_skills(resume_text)
        
        # Calculate individual scores
        skill_score = self.calculate_skill_match(resume_skills, job_skills)
        title_score = self.calculate_title_match(resume_text, job_data.get('job_title', ''))
        
        # Description matching using TF-IDF
        description_score = self._calculate_description_similarity(
            resume_text, 
            job_data.get('job_description', '')
        )
        
        experience_score = self.calculate_experience_match(
            resume_text, 
            job_data.get('experience_level', '')
        )
        
        location_score = self.calculate_location_match(
            resume_text,
            job_data.get('location_display', ''),
            job_data.get('is_remote', False)
        )
        
        # Calculate weighted score
        weighted_score = (
            skill_score * weights['skills'] +
            title_score * weights['title'] +
            description_score * weights['description'] +
            experience_score * weights['experience'] +
            location_score * weights['location']
        )
        
        # Add bonus for high-demand skills
        bonus_score = self._calculate_skill_bonus(resume_skills, job_skills)
        weighted_score += bonus_score
        
        return min(weighted_score, 100)
    
    def _calculate_description_similarity(self, resume_text: str, job_description: str) -> float:
        """Calculate similarity between resume and job description"""
        if not job_description or not resume_text:
            return 0.0
        
        try:
            # Prepare texts
            texts = [resume_text, job_description]
            
            # Fit and transform
            tfidf_matrix = self.description_vectorizer.fit_transform(texts)
            
            # Calculate cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return similarity * 100
            
        except Exception as e:
            logger.warning(f"Error calculating description similarity: {e}")
            return 50.0  # Default score
    
    def _calculate_skill_bonus(self, resume_skills: List[str], job_skills: List[str]) -> float:
        """Calculate bonus score for high-demand or rare skills"""
        if not resume_skills or not job_skills:
            return 0.0
        
        # High-demand skills (adjust as needed)
        high_demand_skills = {
            'python': 5,
            'machine learning': 5,
            'ai': 5,
            'aws': 4,
            'docker': 4,
            'kubernetes': 4,
            'react': 3,
            'typescript': 3,
            'node.js': 3,
            'sql': 2,
            'git': 2
        }
        
        bonus = 0.0
        resume_skills_lower = [skill.lower() for skill in resume_skills]
        job_skills_lower = [skill.lower() for skill in job_skills]
        
        # Check for high-demand skills that are in both resume and job
        for skill, points in high_demand_skills.items():
            if skill in resume_skills_lower and skill in job_skills_lower:
                bonus += points
        
        # Bonus for matching multiple required skills
        matched_skills = set(resume_skills_lower) & set(job_skills_lower)
        if len(matched_skills) >= 5:
            bonus += 10
        elif len(matched_skills) >= 3:
            bonus += 5
        
        return min(bonus, 15)  # Cap bonus at 15 points
    
    def match_resume_to_jobs(self, 
                           resume_text: str, 
                           jobs_df: pd.DataFrame, 
                           top_n: int = 15,
                           min_score: float = 0.0) -> pd.DataFrame:
        """
        Enhanced matching function with multiple scoring factors
        
        Args:
            resume_text: Text of the resume
            jobs_df: DataFrame containing job listings
            top_n: Number of top matches to return
            min_score: Minimum match score to include
        
        Returns:
            DataFrame with matched jobs and scores
        """
        if jobs_df is None or jobs_df.empty:
            logger.warning("No jobs provided for matching")
            return pd.DataFrame()
        
        if not resume_text or len(resume_text.strip()) < 50:
            logger.warning("Resume text too short or empty")
            return pd.DataFrame()
        
        # Make a copy of jobs
        jobs = jobs_df.copy()
        
        # Extract resume skills once
        resume_skills = self.extract_resume_skills(resume_text)
        
        match_scores = []
        match_details = []
        
        logger.info(f"Matching resume against {len(jobs)} jobs...")
        
        for idx, row in jobs.iterrows():
            try:
                job_dict = row.to_dict()
                
                if self.use_weighted_matching:
                    # Calculate weighted match score
                    score = self.calculate_weighted_match_score(resume_text, job_dict)
                else:
                    # Use simple TF-IDF matching
                    score = self._calculate_simple_match(resume_text, job_dict)
                
                # Store score and details
                match_scores.append(score)
                
                # Extract match details for debugging/insights
                job_skills = self.extract_job_skills(job_dict)
                skill_match = self.calculate_skill_match(resume_skills, job_skills)
                
                details = {
                    'skill_match': skill_match,
                    'skills_found': len(set(resume_skills) & set(job_skills)),
                    'skills_required': len(job_skills),
                    'is_remote': job_dict.get('is_remote', False),
                    'experience_match': self.calculate_experience_match(resume_text, job_dict.get('experience_level', ''))
                }
                match_details.append(details)
                
            except Exception as e:
                logger.warning(f"Error matching job {idx}: {e}")
                match_scores.append(0.0)
                match_details.append({})
        
        # Add scores to DataFrame
        jobs['match_score'] = match_scores
        
        # Add match details as JSON string
        jobs['match_details'] = [json.dumps(details) for details in match_details]
        
        # Filter by minimum score
        filtered_jobs = jobs[jobs['match_score'] >= min_score].copy()
        
        # Sort by score
        filtered_jobs = filtered_jobs.sort_values('match_score', ascending=False)
        
        # Add ranking
        filtered_jobs['match_rank'] = range(1, len(filtered_jobs) + 1)
        
        # Add match category based on score
        def categorize_score(score):
            if score >= 85:
                return "Excellent Match"
            elif score >= 70:
                return "Strong Match"
            elif score >= 55:
                return "Good Match"
            elif score >= 40:
                return "Fair Match"
            else:
                return "Basic Match"
        
        filtered_jobs['match_category'] = filtered_jobs['match_score'].apply(categorize_score)
        
        # Calculate confidence score (based on data completeness)
        def calculate_confidence(row):
            confidence = 0.7  # Base confidence
            
            # Increase confidence based on data quality
            if pd.notna(row.get('salary_display')) and str(row.get('salary_display')) != 'Not specified':
                confidence += 0.1
            
            if row.get('has_apply_link', False):
                confidence += 0.1
            
            if row.get('skills_count', 0) > 3:
                confidence += 0.1
            
            return min(confidence, 1.0)
        
        filtered_jobs['confidence'] = filtered_jobs.apply(calculate_confidence, axis=1)
        
        logger.info(f"Found {len(filtered_jobs)} matches above score {min_score}")
        
        # Return top N matches
        return filtered_jobs.head(top_n)
    
    def _calculate_simple_match(self, resume_text: str, job_data: Dict) -> float:
        """Simple TF-IDF matching for backward compatibility"""
        job_text = f"{job_data.get('job_title', '')} {job_data.get('job_description', '')}"
        
        if not job_text.strip():
            return 0.0
        
        try:
            texts = [resume_text, job_text]
            tfidf_matrix = self.title_vectorizer.fit_transform(texts)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return similarity * 100
        except:
            return 0.0
    
    def get_match_insights(self, matched_jobs: pd.DataFrame) -> Dict[str, Any]:
        """Generate insights from matched jobs"""
        if matched_jobs.empty:
            return {}
        
        insights = {
            'top_skills_demanded': [],
            'average_salary': None,
            'remote_ratio': 0.0,
            'common_titles': [],
            'score_distribution': {}
        }
        
        # Extract top demanded skills
        all_job_skills = []
        for skills_json in matched_jobs['skills'].dropna():
            try:
                skills = json.loads(skills_json)
                all_job_skills.extend(skills)
            except:
                pass
        
        skill_counter = Counter(all_job_skills)
        insights['top_skills_demanded'] = skill_counter.most_common(10)
        
        # Calculate average salary if available
        salary_cols = matched_jobs[['salary_min', 'salary_max']].dropna()
        if not salary_cols.empty:
            avg_min = salary_cols['salary_min'].mean()
            avg_max = salary_cols['salary_max'].mean()
            insights['average_salary'] = f"${avg_min:,.0f} - ${avg_max:,.0f}"
        
        # Calculate remote ratio
        remote_count = matched_jobs['is_remote'].sum()
        insights['remote_ratio'] = (remote_count / len(matched_jobs)) * 100
        
        # Most common job titles
        title_counter = Counter(matched_jobs['job_title'].dropna())
        insights['common_titles'] = title_counter.most_common(5)
        
        # Score distribution
        score_bins = [0, 40, 55, 70, 85, 100]
        score_labels = ['Low', 'Fair', 'Good', 'Strong', 'Excellent']
        
        for i in range(len(score_bins) - 1):
            low, high = score_bins[i], score_bins[i + 1]
            count = ((matched_jobs['match_score'] >= low) & (matched_jobs['match_score'] < high)).sum()
            insights['score_distribution'][score_labels[i]] = count
        
        return insights
    
    def generate_resume_gap_analysis(self, resume_text: str, matched_jobs: pd.DataFrame) -> Dict[str, Any]:
        """Analyze gaps between resume and job requirements"""
        if matched_jobs.empty:
            return {}
        
        resume_skills = set(self.extract_resume_skills(resume_text))
        
        # Collect all required skills from top matches
        all_required_skills = set()
        for skills_json in matched_jobs.head(5)['skills'].dropna():
            try:
                skills = set(json.loads(skills_json))
                all_required_skills.update(skills)
            except:
                pass
        
        # Calculate missing skills
        missing_skills = all_required_skills - resume_skills
        
        # Categorize missing skills
        gap_analysis = {
            'missing_skills': sorted(list(missing_skills)),
            'missing_count': len(missing_skills),
            'strengths': sorted(list(resume_skills & all_required_skills)),
            'strength_count': len(resume_skills & all_required_skills),
            'coverage_percentage': (len(resume_skills & all_required_skills) / len(all_required_skills) * 100) if all_required_skills else 0
        }
        
        # Identify critical gaps (high-demand missing skills)
        high_demand_skills = {'python', 'aws', 'docker', 'kubernetes', 'react', 'machine learning', 'sql'}
        gap_analysis['critical_gaps'] = sorted(list(missing_skills & high_demand_skills))
        
        return gap_analysis

# Helper function for backward compatibility
def match_resume_to_jobs_simple(resume_text: str, jobs_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Simple wrapper for backward compatibility"""
    matcher = JobMatcher(use_weighted_matching=False)
    return matcher.match_resume_to_jobs(resume_text, jobs_df, top_n)

# Test function
def test_matcher():
    """Test the JobMatcher functionality"""
    print("🧪 Testing JobMatcher...")
    
    # Sample resume text
    resume_text = """
    Software Engineer with 5 years of experience in Python and JavaScript.
    Proficient in React, Node.js, and AWS. Strong background in building 
    scalable web applications. Experienced with Docker, Kubernetes, and CI/CD.
    Skilled in SQL and NoSQL databases. Excellent problem-solving abilities.
    Location: Open to remote positions.
    """
    
    # Sample job data
    jobs_data = [
        {
            'job_title': 'Senior Python Developer',
            'job_description': 'Looking for experienced Python developer with AWS knowledge. Must have 5+ years of experience with Python and cloud services.',
            'skills': '["Python", "AWS", "Docker", "SQL"]',
            'experience_level': '5+ years',
            'location_display': 'Remote',
            'is_remote': True,
            'salary_display': '$120,000 - $150,000/year'
        },
        {
            'job_title': 'React Frontend Developer',
            'job_description': 'Frontend developer needed with React and TypeScript experience. 3+ years required.',
            'skills': '["React", "TypeScript", "JavaScript", "HTML", "CSS"]',
            'experience_level': '3+ years',
            'location_display': 'New York, NY',
            'is_remote': False,
            'salary_display': '$90,000 - $110,000/year'
        }
    ]
    
    jobs_df = pd.DataFrame(jobs_data)
    
    # Test matcher
    matcher = JobMatcher()
    matches = matcher.match_resume_to_jobs(resume_text, jobs_df, top_n=5)
    
    if not matches.empty:
        print(f"✅ Found {len(matches)} matches")
        print("\nMatch results:")
        for idx, row in matches.iterrows():
            print(f"  {row['job_title']}: {row['match_score']:.1f}%")
        
        # Test insights
        insights = matcher.get_match_insights(matches)
        print(f"\nInsights - Top skills: {insights.get('top_skills_demanded', [])[:3]}")
        
        # Test gap analysis
        gap_analysis = matcher.generate_resume_gap_analysis(resume_text, matches)
        print(f"Gap analysis - Missing {gap_analysis.get('missing_count', 0)} skills")
    
    else:
        print("❌ No matches found")
    
    print("\n🧪 Test completed!")

if __name__ == "__main__":
    test_matcher()