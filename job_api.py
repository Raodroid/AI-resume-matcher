import os
import requests
import pandas as pd
from typing import Dict, List, Optional, Any
import time
import logging
import json
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobSearchAPI:
    """
    Job Search API client for fetching jobs from JSearch API (RapidAPI)
    Optimized for Hugging Face Spaces deployment
    """
    
    def __init__(self):
        self.base_url = "https://jsearch.p.rapidapi.com"
        self.api_key = self._get_api_key()
        self.headers = self._get_headers()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def _get_api_key(self) -> str:
        """
        Fetch API key optimized for Hugging Face Spaces
        Priority order:
        1. Environment variable (Hugging Face Secrets)
        2. Streamlit secrets (st.secrets)
        3. Local .env file (development only)
        
        Returns:
            str: API key or empty string if not found
        """
        # Debug info
        debug_info = []
        
        # 1. Environment variable (Primary for Hugging Face)
        key = os.getenv("RAPIDAPI_KEY")
        if key and key.strip():
            debug_info.append(f"✅ Found in os.getenv: {key[:8]}...")
            logger.info(f"API key loaded from environment variable: {key[:8]}...")
            return key.strip()
        else:
            debug_info.append("❌ Not in os.getenv")
        
        # 2. Streamlit secrets (Alternative for Hugging Face)
        try:
            import streamlit as st
            if hasattr(st, "secrets") and st.secrets:
                key = st.secrets.get("RAPIDAPI_KEY")
                if key and key.strip():
                    debug_info.append(f"✅ Found in st.secrets: {key[:8]}...")
                    logger.info(f"API key loaded from st.secrets: {key[:8]}...")
                    return key.strip()
                else:
                    debug_info.append("❌ Not in st.secrets")
        except Exception as e:
            debug_info.append(f"❌ st.secrets error: {str(e)}")
        
        # 3. Local .env file (Development only)
        try:
            from dotenv import load_dotenv
            load_dotenv()
            key = os.getenv("RAPIDAPI_KEY")
            if key and key.strip():
                debug_info.append(f"✅ Found in .env: {key[:8]}...")
                logger.info(f"API key loaded from .env file: {key[:8]}...")
                return key.strip()
            else:
                debug_info.append("❌ Not in .env")
        except ImportError:
            debug_info.append("❌ python-dotenv not installed")
        except Exception as e:
            debug_info.append(f"❌ .env error: {str(e)}")
        
        # Log debug info
        logger.warning("API Key Debug: " + " | ".join(debug_info))
        
        # Show user-friendly error
        try:
            import streamlit as st
            with st.sidebar:
                st.error("""
                🔑 **API Key Configuration Error**
                
                RapidAPI key not found. Please ensure:
                
                **On Hugging Face:**
                1. Go to Space → Settings → Repository Secrets
                2. Add: `RAPIDAPI_KEY = your_key_here`
                
                **Local Development:**
                1. Create `.env` file in project root
                2. Add: `RAPIDAPI_KEY=your_key_here`
                
                Get your key from: https://rapidapi.com/developer/dashboard
                """)
        except:
            pass
        
        return ""
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        if not self.api_key:
            return {}
        
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            "Content-Type": "application/json"
        }
    
    def search_jobs(
        self,
        query: str,
        location: str = "",
        num_pages: int = 1,
        employment_types: Optional[List[str]] = None,
        date_posted: str = "all",
        remote_only: bool = False,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        Search for jobs using JSearch API
        
        Args:
            query: Job search query (e.g., "software engineer")
            location: Location for job search (e.g., "New York")
            num_pages: Number of pages to fetch (1-5)
            employment_types: List of employment types
            date_posted: "all", "today", "3days", "week", "month"
            remote_only: Filter for remote jobs only
            **kwargs: Additional API parameters
            
        Returns:
            pandas.DataFrame: DataFrame of job listings or None if error
        """
        # Check API key
        if not self.api_key:
            logger.error("No API key available for job search")
            return None
        
        # Validate input
        if not query or not query.strip():
            logger.error("Empty search query")
            return None
        
        # Prepare parameters
        search_query = query.strip()
        if location and location.strip():
            search_query += f" in {location.strip()}"
        
        params = {
            "query": search_query,
            "page": "1",
            "num_pages": str(min(num_pages, 5)),  # API limit
            "date_posted": date_posted,
        }
        
        # Add optional parameters
        if employment_types:
            params["employment_types"] = ",".join(employment_types)
        if remote_only:
            params["remote_jobs_only"] = "true"
        
        # Add any additional kwargs
        params.update(kwargs)
        
        try:
            logger.info(f"Searching jobs: {search_query}")
            
            # Make API request
            response = self.session.get(
                f"{self.base_url}/search",
                params=params,
                timeout=15
            )
            
            # Check response
            if response.status_code == 200:
                data = response.json()
                return self._parse_jobs(data)
            elif response.status_code == 401:
                logger.error("API key is invalid or expired")
                self._show_api_error("Invalid API key. Please check your RapidAPI subscription.")
            elif response.status_code == 403:
                logger.error("API key missing or insufficient permissions")
                self._show_api_error("API key missing or insufficient permissions. Check Hugging Face Secrets.")
            elif response.status_code == 429:
                logger.error("Rate limit exceeded")
                self._show_api_error("Rate limit exceeded. Please try again later.")
            else:
                logger.error(f"API error {response.status_code}: {response.text[:200]}")
                self._show_api_error(f"API error {response.status_code}. Please try again.")
                
            return None
            
        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            self._show_api_error("Request timed out. Please try again.")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            self._show_api_error("Connection error. Please check your internet.")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            self._show_api_error(f"Unexpected error: {str(e)}")
            return None
    
    def _parse_jobs(self, data: Dict) -> pd.DataFrame:
        """
        Parse API response into DataFrame
        
        Args:
            data: Raw API response
            
        Returns:
            pandas.DataFrame: Cleaned job listings
        """
        jobs = []
        
        if not data.get("data"):
            logger.warning("No job data in API response")
            return pd.DataFrame()
        
        for job in data["data"]:
            try:
                # Extract salary information
                salary_info = job.get("job_salary", "") or ""
                min_salary, max_salary = self._extract_salary(salary_info)
                
                # Extract required skills
                required_skills = self._extract_skills(job)
                
                # Create job record
                job_record = {
                    "job_title": job.get("job_title", ""),
                    "employer_name": job.get("employer_name", ""),
                    "employer_logo": job.get("employer_logo", ""),
                    "job_description": job.get("job_description", "")[:1000],  # Limit length
                    "job_apply_link": job.get("job_apply_link", ""),
                    "job_city": job.get("job_city", ""),
                    "job_state": job.get("job_state", ""),
                    "job_country": job.get("job_country", "US"),
                    "job_employment_type": job.get("job_employment_type", ""),
                    "job_is_remote": job.get("job_is_remote", False),
                    "job_posted_at": job.get("job_posted_at_datetime_utc", ""),
                    "job_salary": salary_info,
                    "job_min_salary": min_salary,
                    "job_max_salary": max_salary,
                    "job_required_skills": ", ".join(required_skills),
                    "job_required_experience": job.get("job_required_experience", ""),
                    "job_required_education": job.get("job_required_education", ""),
                    "job_highlights": json.dumps(job.get("job_highlights", {})),
                    "original_index": len(jobs)
                }
                jobs.append(job_record)
                
            except Exception as e:
                logger.warning(f"Error parsing job {job.get('job_id', 'unknown')}: {str(e)}")
                continue
        
        if not jobs:
            return pd.DataFrame()
        
        df = pd.DataFrame(jobs)
        
        # Clean up DataFrame
        df = self._clean_dataframe(df)
        
        logger.info(f"Successfully parsed {len(df)} jobs")
        return df
    
    def _extract_salary(self, salary_text: str) -> tuple:
        """
        Extract min and max salary from salary text
        
        Args:
            salary_text: Salary description text
            
        Returns:
            tuple: (min_salary, max_salary) as floats
        """
        if not salary_text:
            return 0.0, 0.0
        
        # Common patterns
        import re
        
        # Pattern for $XX,XXX - $YY,YYY
        pattern = r'\$([\d,]+)\s*[-–]\s*\$([\d,]+)'
        match = re.search(pattern, salary_text)
        
        if match:
            try:
                min_sal = float(match.group(1).replace(',', ''))
                max_sal = float(match.group(2).replace(',', ''))
                return min_sal, max_sal
            except:
                pass
        
        # Pattern for single value
        pattern_single = r'\$([\d,]+)'
        match = re.search(pattern_single, salary_text)
        
        if match:
            try:
                salary = float(match.group(1).replace(',', ''))
                return salary, salary
            except:
                pass
        
        return 0.0, 0.0
    
    def _extract_skills(self, job: Dict) -> List[str]:
        """
        Extract skills from job description
        
        Args:
            job: Job dictionary
            
        Returns:
            List of skills
        """
        skills = []
        
        # Common tech skills to look for
        tech_skills = [
            'python', 'java', 'javascript', 'react', 'node.js', 'aws',
            'docker', 'kubernetes', 'sql', 'nosql', 'mongodb', 'postgresql',
            'machine learning', 'ai', 'data science', 'tensorflow', 'pytorch',
            'git', 'ci/cd', 'azure', 'gcp', 'linux', 'agile', 'scrum'
        ]
        
        # Check description and title
        description = (job.get('job_description', '') + ' ' + 
                      job.get('job_title', '')).lower()
        
        for skill in tech_skills:
            if skill.lower() in description:
                skills.append(skill.title())
        
        # Remove duplicates and limit
        skills = list(set(skills))[:10]
        
        return skills
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean the jobs DataFrame
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        # Make a copy
        df_clean = df.copy()
        
        # Fill missing values
        df_clean.fillna({
            'job_title': 'Unknown Position',
            'employer_name': 'Unknown Company',
            'job_description': 'No description available',
            'job_city': 'Remote',
            'job_country': 'US'
        }, inplace=True)
        
        # Clean text columns
        text_columns = ['job_title', 'employer_name', 'job_description']
        for col in text_columns:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str).str.strip()
        
        # Ensure numeric columns
        numeric_cols = ['job_min_salary', 'job_max_salary']
        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
        
        # Sort by salary (if available) and freshness
        if 'job_max_salary' in df_clean.columns:
            df_clean = df_clean.sort_values(
                by=['job_max_salary', 'job_posted_at'],
                ascending=[False, False]
            )
        
        return df_clean.reset_index(drop=True)
    
    def _show_api_error(self, message: str):
        """
        Display API error message to user via Streamlit
        
        Args:
            message: Error message to display
        """
        try:
            import streamlit as st
            st.error(f"**API Error**: {message}")
            
            # Add troubleshooting tips
            with st.expander("Troubleshooting Tips"):
                st.write("""
                1. **Check API Key**: Ensure `RAPIDAPI_KEY` is set in Hugging Face Secrets
                2. **Verify Subscription**: Confirm JSearch API subscription is active on RapidAPI
                3. **Rate Limits**: Free tier has limited requests per day
                4. **Network**: Check if Hugging Face can reach RapidAPI
                """)
                
        except:
            # Fallback to logging if Streamlit not available
            logger.error(f"API Error: {message}")
    
    def test_connection(self) -> bool:
        """
        Test API connection
        
        Returns:
            bool: True if connection successful
        """
        if not self.api_key:
            logger.error("No API key to test connection")
            return False
        
        try:
            # Simple test request
            response = self.session.get(
                f"{self.base_url}/search",
                params={"query": "software engineer", "page": "1", "num_pages": "1"},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ API connection test successful")
                return True
            else:
                logger.error(f"❌ API test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ API test error: {str(e)}")
            return False


# Helper function for quick usage
def search_jobs_simple(
    query: str,
    location: str = "",
    num_pages: int = 1
) -> Optional[pd.DataFrame]:
    """
    Simple wrapper function for job search
    
    Args:
        query: Job search query
        location: Optional location
        num_pages: Number of pages (1-5)
        
    Returns:
        DataFrame of jobs or None if error
    """
    api = JobSearchAPI()
    return api.search_jobs(query=query, location=location, num_pages=num_pages)


# For testing/debugging
if __name__ == "__main__":
    # Test the API
    print("Testing Job Search API...")
    
    api = JobSearchAPI()
    
    # Test connection
    if api.test_connection():
        print("✅ API connection successful")
        
        # Test search
        jobs_df = api.search_jobs(
            query="software engineer",
            location="San Francisco",
            num_pages=1
        )
        
        if jobs_df is not None and not jobs_df.empty:
            print(f"✅ Found {len(jobs_df)} jobs")
            print(jobs_df[['job_title', 'employer_name', 'job_city', 'job_max_salary']].head())
        else:
            print("❌ No jobs found or error occurred")
    else:
        print("❌ API connection failed")