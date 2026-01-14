import requests
import pandas as pd
import os
from dotenv import load_dotenv
import json

class JobSearchAPI:
    def __init__(self, api_key: str = None):
        """Initialize with API key from .env or parameter"""
        # Load .env file
        load_dotenv()
        
        # Get API key
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("RAPIDAPI_KEY") or ""
        
        self.base_url = "https://jsearch.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
    
    def search_jobs(self, query: str, location: str, num_pages: int = 1):
        """Search for jobs - simplified version"""
        if not self.api_key:
            print("❌ No API key found")
            print("   Create .env file with: RAPIDAPI_KEY=your_key")
            return pd.DataFrame()
        
        all_jobs = []
        
        for page in range(1, num_pages + 1):
            try:
                params = {
                    "query": f"{query} in {location}",
                    "page": str(page),
                    "num_pages": "1"
                }
                
                response = requests.get(
                    f"{self.base_url}/search",
                    headers=self.headers,
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("status") == "OK" and data.get("data"):
                        for job in data["data"]:
                            # Simple parsing
                            job_info = {
                                "job_id": job.get("job_id", ""),
                                "job_title": job.get("job_title", "Not specified"),
                                "employer_name": job.get("employer_name", "Not specified"),
                                "job_city": job.get("job_city", ""),
                                "job_state": job.get("job_state", ""),
                                "job_country": job.get("job_country", ""),
                                "location": f"{job.get('job_city', '')}, {job.get('job_state', '')}, {job.get('job_country', '')}",
                                "job_salary": job.get("job_salary", "Not specified"),
                                "job_description": job.get("job_description", "")[:500] + "..." if job.get("job_description") else "",
                                "job_apply_link": job.get("job_apply_link", ""),
                                "job_is_remote": job.get("job_is_remote", False)
                            }
                            all_jobs.append(job_info)
                
            except Exception as e:
                print(f"Error on page {page}: {e}")
                break
        
        if all_jobs:
            return pd.DataFrame(all_jobs)
        else:
            return pd.DataFrame()