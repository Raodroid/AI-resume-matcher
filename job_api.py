import requests
import pandas as pd
import streamlit as st
import os
from typing import List, Dict, Optional

class JobSearchAPI:
    """Handle job search API integration"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or self._get_api_key()
        self.base_url = "https://jsearch.p.rapidapi.com"
        
    def _get_api_key(self) -> str:
        """Get API key from secrets or environment"""
        try:
            # Try to get from Streamlit secrets
            return st.secrets["RAPIDAPI_KEY"]
        except:
            # Try environment variable
            return os.getenv("RAPIDAPI_KEY", "")
    
    def search_jobs(self, query: str = "software engineer", 
                   location: str = "United States", 
                   num_pages: int = 1) -> pd.DataFrame:
        """Search for jobs using JSearch API"""
        
        if not self.api_key:
            st.error("API key not found. Please set RAPIDAPI_KEY in secrets or environment.")
            return pd.DataFrame()
        
        url = f"{self.base_url}/search"
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        all_jobs = []
        
        for page in range(1, num_pages + 1):
            querystring = {
                "query": f"{query} in {location}",
                "page": str(page),
                "num_pages": "1"
            }
            
            try:
                response = requests.get(url, headers=headers, params=querystring)
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") == "OK" and data.get("data"):
                    for job in data["data"]:
                        job_data = self._parse_job(job)
                        all_jobs.append(job_data)
                
                # Small delay to avoid rate limiting
                import time
                time.sleep(0.5)
                
            except requests.exceptions.RequestException as e:
                st.error(f"API request failed: {e}")
                break
            except Exception as e:
                st.error(f"Error processing API response: {e}")
                break
        
        return pd.DataFrame(all_jobs) if all_jobs else pd.DataFrame()
    
    def _parse_job(self, job: Dict) -> Dict:
        """Parse API job data into standardized format"""
        
        # Extract salary information
        salary = "Not specified"
        if job.get("job_salary"):
            salary = job["job_salary"]
        elif job.get("job_min_salary") and job.get("job_max_salary"):
            salary = f"${job['job_min_salary']} - ${job['job_max_salary']}"
        
        # Extract location
        location_parts = []
        if job.get("job_city"):
            location_parts.append(job["job_city"])
        if job.get("job_state"):
            location_parts.append(job["job_state"])
        if job.get("job_country"):
            location_parts.append(job["job_country"])
        location = ", ".join(location_parts) if location_parts else "Not specified"
        
        # Extract skills from job highlights
        skills = []
        if job.get("job_highlights"):
            highlights = job["job_highlights"]
            if highlights.get("Qualifications"):
                skills.extend(self._extract_skills_from_text(str(highlights["Qualifications"])))
            if highlights.get("Responsibilities"):
                skills.extend(self._extract_skills_from_text(str(highlights["Responsibilities"])))
        
        # Use job description for skills extraction if no highlights
        if not skills and job.get("job_description"):
            skills = self._extract_skills_from_text(job["job_description"])
        
        # Unique skills
        skills = list(set(skills))[:10]  # Limit to top 10 skills
        
        return {
            "job_id": job.get("job_id", ""),
            "job_title": job.get("job_title", "Not specified"),
            "company": job.get("employer_name", "Not specified"),
            "location": location,
            "salary": salary,
            "employment_type": job.get("job_employment_type", "Not specified"),
            "description": job.get("job_description", "No description available"),
            "skills": skills,
            "apply_link": job.get("job_apply_link", ""),
            "posted_at": job.get("job_posted_at", ""),
            "remote": job.get("job_is_remote", False),
            "logo": job.get("employer_logo", "")
        }
    
    def _extract_skills_from_text(self, text: str) -> List[str]:
        """Extract potential skills from text"""
        common_skills = [
            "python", "java", "javascript", "sql", "html", "css",
            "react", "angular", "vue", "aws", "azure", "gcp",
            "docker", "kubernetes", "snowflake", "dbt",
            "machine learning", "data science", "data engineering",
            "etl", "elt", "airflow", "spark", "hadoop",
            "tableau", "power bi", "excel", "git", "github",
            "agile", "scrum", "devops", "ci/cd"
        ]
        
        found_skills = []
        text_lower = str(text).lower()
        
        for skill in common_skills:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        return found_skills
    
    def get_job_details(self, job_id: str) -> Optional[Dict]:
        """Get detailed information about a specific job"""
        url = f"{self.base_url}/job-details"
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        querystring = {
            "job_id": job_id,
            "country": "us",
            "language": "en"
        }
        
        try:
            response = requests.get(url, headers=headers, params=querystring)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") == "OK" and data.get("data"):
                return self._parse_job(data["data"][0])
                
        except Exception as e:
            st.error(f"Error fetching job details: {e}")
        
        return None