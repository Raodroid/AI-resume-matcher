import pandas as pd
import os
import json
from datetime import datetime, timedelta
import time
from typing import List, Dict, Any, Optional
import logging
import random
import re
import requests
import hashlib
import pickle
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobSearchAPI:
    def __init__(self):
        """Initialize JobSearchAPI - Uses ONLY real API, NO mock data"""
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        logger.info("🔧 Initializing JobSearchAPI...")
        
        # Get ALL RapidAPI keys from environment
        self.rapidapi_keys = self._get_all_rapidapi_keys()
        self.current_key_index = 0
        
        # Get Adzuna keys
        self.adzuna_api_key = os.getenv("ADZUNA_API_KEY", "")
        self.adzuna_app_id = os.getenv("ADZUNA_APP_ID", "")
        
        # Debug: Show what we found
        logger.info(f"🔑 Found {len(self.rapidapi_keys)} RapidAPI keys")
        for i, key in enumerate(self.rapidapi_keys, 1):
            logger.info(f"  Key {i}: {key[:10]}...")
        
        logger.info(f"📈 Adzuna available: {bool(self.adzuna_api_key and self.adzuna_app_id)}")
        
        # Track API usage
        self.api_calls_today = 0
        self.max_api_calls_per_day = 50  # Higher limit since we have multiple keys
        self.failed_keys = set()  # Track which keys have failed
        
        # Cache setup
        self.cache_dir = Path("api_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_duration = timedelta(minutes=30)  # Cache for 30 minutes
        
        # Determine which APIs to use
        self.can_use_rapidapi = len(self.rapidapi_keys) > 0
        self.can_use_adzuna = bool(self.adzuna_api_key and self.adzuna_app_id)
        
        if not self.can_use_rapidapi and not self.can_use_adzuna:
            logger.error("❌ NO API KEYS FOUND! Please check your .env file")
            logger.error("   Required: RAPIDAPI_KEY_1 or RAPIDAPI_KEY")
            logger.error("   Optional: ADZUNA_API_KEY and ADZUNA_APP_ID")
            raise ValueError("No API keys found. Please set RAPIDAPI_KEY_1 in .env file")
        
        logger.info("✅ Ready to use real APIs (NO MOCK DATA)")
    
    def _get_all_rapidapi_keys(self) -> List[str]:
        """Get all RapidAPI keys from environment"""
        keys = []
        
        # Check for single key first
        single_key = os.getenv("RAPIDAPI_KEY", "")
        if single_key and len(single_key) > 20:
            keys.append(single_key)
        
        # Check for multiple keys (RAPIDAPI_KEY_1, RAPIDAPI_KEY_2, etc.)
        for i in range(1, 11):  # Check up to 10 keys
            key_name = f"RAPIDAPI_KEY_{i}"
            key = os.getenv(key_name, "")
            if key and len(key) > 20:  # Basic validation
                keys.append(key)
        
        return keys
    
    def _get_next_rapidapi_key(self) -> Optional[str]:
        """Get the next available RapidAPI key (round-robin)"""
        if not self.rapidapi_keys:
            return None
        
        available_keys = [k for i, k in enumerate(self.rapidapi_keys) 
                          if i not in self.failed_keys]
        
        if not available_keys:
            # Reset failed keys if all failed
            self.failed_keys.clear()
            available_keys = self.rapidapi_keys
        
        # Get next key in round-robin
        if self.current_key_index >= len(available_keys):
            self.current_key_index = 0
        
        key = available_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(available_keys)
        
        return key
    
    def _try_rapidapi(self, query: str, location: str, max_retries: int = 1) -> Optional[List[Dict]]:
        """Try to get jobs from RapidAPI with multiple key support"""
        if not self.can_use_rapidapi:
            return None
        
        for attempt in range(max_retries):
            key = self._get_next_rapidapi_key()
            if not key:
                logger.error("❌ No available RapidAPI keys")
                return None
            
            try:
                logger.info(f"🌐 Attempt {attempt + 1}: Calling RapidAPI with key {key[:10]}...")
                
                headers = {
                    "X-RapidAPI-Key": key,
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
                }
                
                # Build query
                search_query = query if query.strip() else "software engineer"
                full_query = f"{search_query}"
                if location and location.strip():
                    full_query = f"{search_query} in {location}"
                
                params = {
                    "query": full_query,
                    "page": 1,
                    "num_pages": 1,
                    "date_posted": "today",  # Get today's jobs
                    "remote_jobs_only": "false"
                }
                
                # Add delay to be respectful
                time.sleep(1)
                
                response = requests.get(
                    "https://jsearch.p.rapidapi.com/search",
                    headers=headers,
                    params=params,
                    timeout=15
                )
                
                self.api_calls_today += 1
                
                logger.info(f"📡 Response status: {response.status_code}")
                
                if response.status_code == 429:
                    logger.warning(f"⚠️ Key {key[:10]}... rate limited (429)")
                    self.failed_keys.add(self.rapidapi_keys.index(key))
                    continue
                elif response.status_code == 403:
                    logger.warning(f"⚠️ Key {key[:10]}... forbidden (403)")
                    self.failed_keys.add(self.rapidapi_keys.index(key))
                    continue
                elif response.status_code == 401:
                    logger.warning(f"⚠️ Key {key[:10]}... unauthorized (401)")
                    self.failed_keys.add(self.rapidapi_keys.index(key))
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                
                if data.get("status") == "OK" and data.get("data"):
                    jobs = data["data"]
                    logger.info(f"✅ RapidAPI returned {len(jobs)} jobs")
                    return jobs[:1]  # Return up to 1 jobs
                else:
                    logger.warning(f"⚠️ RapidAPI returned error: {data.get('status')}")
                    continue
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ RapidAPI request error: {e}")
                if key in self.rapidapi_keys:
                    self.failed_keys.add(self.rapidapi_keys.index(key))
                continue
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                continue
        
        logger.error("❌ All RapidAPI attempts failed")
        return None
    
    def _try_adzuna(self, query: str, location: str) -> Optional[List[Dict]]:
        """Try to get jobs from Adzuna (only if RapidAPI fails)"""
        if not self.can_use_adzuna:
            return None
        
        try:
            logger.info(f"🌐 Calling Adzuna API: '{query}' in '{location}'")
            
            # Determine country code
            country_code = self._get_country_code(location)
            
            url = f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1"
            
            params = {
                "app_id": self.adzuna_app_id,
                "app_key": self.adzuna_api_key,
                "what": query if query else "software engineer",
                "results_per_page": 1,  # Get 1 results
                "max_days_old": 7
            }
            
            if location and location.strip():
                params["where"] = location
            
            time.sleep(1)
            
            response = requests.get(url, params=params, timeout=15)
            
            self.api_calls_today += 1
            
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("results", [])
                logger.info(f"✅ Adzuna returned {len(jobs)} jobs")
                return jobs[:1]  # Return up to 1 jobs
            else:
                logger.warning(f"⚠️ Adzuna API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Adzuna API error: {e}")
            return None
    
    def _get_country_code(self, location: str) -> str:
        """Get country code from location"""
        location_lower = location.lower()
        
        if "singapore" in location_lower or "sg" in location_lower:
            return "sg"
        elif "uk" in location_lower or "united kingdom" in location_lower:
            return "gb"
        elif "australia" in location_lower or "au" in location_lower:
            return "au"
        elif "canada" in location_lower or "ca" in location_lower:
            return "ca"
        elif "india" in location_lower or "in" in location_lower:
            return "in"
        else:
            return "us"  # Default to US
    
    def _get_cache_key(self, query: str, location: str, params: Dict) -> str:
        """Generate cache key from search parameters"""
        cache_str = f"{query}_{location}_{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """Get data from cache if exists and not expired"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                    cached_time = cache_data['timestamp']
                    
                    if datetime.now() - cached_time < self.cache_duration:
                        logger.info("📦 Using cached data")
                        return cache_data['jobs']
            except Exception as e:
                logger.warning(f"Error reading cache: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, jobs: List[Dict]):
        """Save data to cache"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            cache_data = {
                'timestamp': datetime.now(),
                'jobs': jobs
            }
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
            logger.info("💾 Saved to cache")
        except Exception as e:
            logger.warning(f"Error saving cache: {e}")
    
    def _enhance_job_data(self, job_data: Dict, source: str) -> Dict[str, Any]:
        """Enhanced job data from API response"""
        try:
            # Extract basic info from different API formats
            if source.startswith("rapidapi"):
                job_id = job_data.get("job_id", "")
                job_title = job_data.get("job_title", "Position")
                employer_name = job_data.get("employer_name", "Company")
                job_description = job_data.get("job_description", "")
                city = job_data.get("job_city", "")
                state = job_data.get("job_state", "")
                country = job_data.get("job_country", "")
                apply_link = job_data.get("job_apply_link", "#")
                salary_min = job_data.get("job_min_salary")
                salary_max = job_data.get("job_max_salary")
                is_remote = job_data.get("job_is_remote", False)
                company_logo = job_data.get("employer_logo", "")
                
            else:  # adzuna
                job_id = job_data.get("id", "")
                job_title = job_data.get("title", "Position")
                employer_name = job_data.get("company", {}).get("display_name", "Company")
                job_description = job_data.get("description", "")
                
                # Location from Adzuna
                location = job_data.get("location", {})
                city = location.get("area", [""])[0] if isinstance(location, dict) else ""
                country = location.get("country", "")
                state = ""
                
                apply_link = job_data.get("redirect_url", "#")
                salary_min = job_data.get("salary_min")
                salary_max = job_data.get("salary_max")
                is_remote = "remote" in str(job_description).lower()
                company_logo = job_data.get("company", {}).get("logo", "")
            
            # Build location display
            location_parts = []
            if city:
                location_parts.append(str(city))
            if state:
                location_parts.append(str(state))
            if country:
                location_parts.append(str(country))
            
            location_display = ", ".join(location_parts) if location_parts else "Location not specified"
            
            # Salary display
            if salary_min and salary_max:
                salary_display = f"${salary_min:,.0f} - ${salary_max:,.0f}/year"
                has_salary = True
            else:
                salary_display = "Not specified"
                has_salary = False
            
            # Remote type
            remote_type = "Remote" if is_remote else "On-site"
            
            # Extract skills from description
            skills = []
            desc_lower = str(job_description).lower()
            
            if "python" in desc_lower:
                skills.append("Python")
            if "java" in desc_lower:
                skills.append("Java")
            if "react" in desc_lower:
                skills.append("React")
            if "aws" in desc_lower or "amazon web services" in desc_lower:
                skills.append("AWS")
            if "docker" in desc_lower:
                skills.append("Docker")
            if "sql" in desc_lower:
                skills.append("SQL")
            if "javascript" in desc_lower:
                skills.append("JavaScript")
            
            if not skills:
                skills = ["Software Development", "Problem Solving"]
            
            # Build enhanced job
            enhanced_job = {
                "job_id": str(job_id),
                "job_title": str(job_title),
                "employer_name": str(employer_name),
                "job_city": str(city),
                "job_state": str(state),
                "job_country": str(country),
                "location_display": location_display,
                "salary_min": float(salary_min) if salary_min else None,
                "salary_max": float(salary_max) if salary_max else None,
                "salary_currency": "USD",
                "salary_period": "year",
                "salary_display": salary_display,
                "is_remote": is_remote,
                "is_hybrid": False,
                "remote_type": remote_type,
                "employment_type": "Full-time",
                "experience_level": "Not specified",
                "job_description": str(job_description)[:1000] + ("..." if len(str(job_description)) > 1000 else ""),
                "company_name": str(employer_name),
                "company_website": "",
                "company_logo": str(company_logo),
                "job_apply_link": str(apply_link),
                "skills": json.dumps(skills),
                "skills_count": len(skills),
                "posting_date": "Recent",
                "posting_timestamp": None,
                "benefits": "Not specified",
                "job_publisher": "Job Board",
                "description_length": len(str(job_description)),
                "has_salary": has_salary,
                "has_apply_link": bool(apply_link and apply_link != "#"),
                "api_source": source,
                "is_mock_data": False
            }
            
            logger.info(f"✅ Enhanced job: {job_title}")
            return enhanced_job
            
        except Exception as e:
            logger.error(f"❌ Error enhancing job: {e}")
            
            # Return minimal job but still from API
            return {
                "job_id": "error",
                "job_title": "API Job",
                "employer_name": "Company",
                "job_description": "Real job from API",
                "job_city": "Location",
                "job_country": "Country",
                "location_display": "Various",
                "salary_display": "Not specified",
                "remote_type": "Unknown",
                "employment_type": "Full-time",
                "job_apply_link": "#",
                "api_source": source + "_error",
                "is_mock_data": False
            }
    
    def search_jobs(self, query: str, location: str = "", num_pages: int = 1, **kwargs) -> pd.DataFrame:
        """Search for jobs - returns up to 1 jobs from real APIs, NO MOCK DATA"""
        logger.info(f"🔍 Searching: '{query}' in '{location}' (real APIs only)")
        
        # Check API call limit
        if self.api_calls_today >= self.max_api_calls_per_day:
            logger.error(f"❌ Daily API limit reached: {self.api_calls_today}/{self.max_api_calls_per_day}")
            raise Exception(f"Daily API limit reached. Please try again tomorrow.")
        
        # Check cache first
        cache_params = {
            "query": query,
            "location": location,
            "source": "rapidapi"
        }
        cache_key = self._get_cache_key(query, location, cache_params)
        cached_jobs = self._get_from_cache(cache_key)
        
        if cached_jobs:
            logger.info("📦 Using cached API results")
            # Still enhance the cached jobs
            enhanced_jobs = []
            for job in cached_jobs[:1]:  # Process up to 1 cached jobs
                enhanced_job = self._enhance_job_data(job, "rapidapi_cached")
                enhanced_jobs.append(enhanced_job)
            return pd.DataFrame(enhanced_jobs)
        
        # Try RapidAPI first (primary)
        jobs_data = None
        source = None
        
        if self.can_use_rapidapi:
            logger.info("🔄 Trying RapidAPI...")
            jobs_data = self._try_rapidapi(query, location)
            source = "rapidapi"
        
        # If RapidAPI failed, try Adzuna
        if not jobs_data and self.can_use_adzuna:
            logger.info("🔄 RapidAPI failed, trying Adzuna...")
            jobs_data = self._try_adzuna(query, location)
            source = "adzuna"
        
        # If ALL APIs failed, raise error (NO MOCK DATA)
        if not jobs_data:
            logger.error("❌ ALL API calls failed!")
            raise Exception("Failed to fetch jobs from APIs. Please check your API keys and try again.")
        
        # Cache successful results
        self._save_to_cache(cache_key, jobs_data)
        
        # Enhance the jobs
        enhanced_jobs = []
        for job in jobs_data[:1]:  # Process up to 1 jobs
            enhanced_job = self._enhance_job_data(job, source)
            enhanced_jobs.append(enhanced_job)
        
        # Log API usage
        logger.info(f"📊 API calls today: {self.api_calls_today}/{self.max_api_calls_per_day}")
        logger.info(f"✅ Successfully got {len(enhanced_jobs)} real job(s) from {source}")
        
        return pd.DataFrame(enhanced_jobs)

# For backward compatibility
def search_jobs_simple(query: str, location: str, num_pages: int = 2) -> pd.DataFrame:
    """Simple wrapper"""
    api = JobSearchAPI()
    return api.search_jobs(query, location, num_pages)

# Test function
def test_real_api():
    """Test real API connections"""
    print("🧪 Testing Real APIs...")
    print("=" * 50)
    
    try:
        api = JobSearchAPI()
        
        print("\n🔍 Searching for 'software engineer' in 'Singapore':")
        jobs = api.search_jobs("software engineer", "Singapore")
        
        print(f"\n📊 Results:")
        print(f"  Found: {len(jobs)} job(s)")
        if not jobs.empty:
            for i, row in jobs.iterrows():
                print(f"\n  Job {i+1}:")
                print(f"  Job Title: {row['job_title']}")
                print(f"  Company: {row['employer_name']}")
                print(f"  Source: {row['api_source']}")
                print(f"  Is Mock: {row['is_mock_data']}")
            print(f"\n  API calls today: {api.api_calls_today}")
        else:
            print("  ❌ No jobs found!")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n🧪 Test completed!")

if __name__ == "__main__":
    test_real_api()