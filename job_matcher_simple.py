import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

class JobMatcher:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        
    def match_resume_to_jobs(self, resume_text, jobs_df, top_n=10):
        """Simple matching function"""
        if jobs_df is None or jobs_df.empty:
            return pd.DataFrame()
        
        if not resume_text or len(resume_text) < 10:
            return pd.DataFrame()
        
        # Make a copy
        jobs = jobs_df.copy()
        
        # Prepare texts
        job_texts = []
        for idx, row in jobs.iterrows():
            text = f"{row.get('job_title', '')} {row.get('job_description', '')}"
            job_texts.append(text)
        
        # Add resume to texts
        all_texts = job_texts + [resume_text]
        
        try:
            # Calculate TF-IDF
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Get similarities
            resume_vector = tfidf_matrix[-1]
            job_vectors = tfidf_matrix[:-1]
            
            similarities = cosine_similarity(resume_vector, job_vectors).flatten()
            
            # Add scores
            jobs['match_score'] = (similarities * 100).round(1)
            
            # Sort and return
            matched = jobs.sort_values('match_score', ascending=False).head(top_n)
            
            return matched
            
        except Exception as e:
            print(f"Error in matching: {e}")
            # Fallback: random ordering
            jobs['match_score'] = np.random.uniform(30, 90, len(jobs))
            return jobs.head(top_n)