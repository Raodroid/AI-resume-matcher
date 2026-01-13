import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re

class JobMatcher:
    """Improved job matching with TF-IDF and keyword analysis"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
        self.common_skills = [
            'python', 'java', 'javascript', 'sql', 'html', 'css',
            'react', 'angular', 'vue', 'aws', 'azure', 'gcp',
            'docker', 'kubernetes', 'snowflake', 'dbt',
            'machine learning', 'data science', 'data engineering',
            'etl', 'elt', 'airflow', 'spark', 'hadoop',
            'tableau', 'power bi', 'excel', 'git', 'github',
            'agile', 'scrum', 'devops', 'ci/cd'
        ]
    
    def match_resume_to_jobs(self, resume_text: str, jobs_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """
        Match resume to jobs using TF-IDF cosine similarity and skill matching
        
        Args:
            resume_text: Text from resume
            jobs_df: DataFrame with job listings
            top_n: Number of top matches to return
        
        Returns:
            DataFrame with matched jobs and scores
        """
        if jobs_df.empty:
            return pd.DataFrame()
        
        # Create copies to avoid modifying original
        jobs = jobs_df.copy()
        resume = resume_text.lower()
        
        # Prepare text for TF-IDF
        job_descriptions = []
        for idx, row in jobs.iterrows():
            desc = str(row.get('description', ''))
            skills = row.get('skills', [])
            if isinstance(skills, list):
                desc += ' ' + ' '.join(skills)
            job_descriptions.append(desc)
        
        # Add resume to corpus
        all_texts = job_descriptions + [resume]
        
        # Calculate TF-IDF matrix
        try:
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Calculate cosine similarity between resume and each job
            resume_vector = tfidf_matrix[-1]
            job_vectors = tfidf_matrix[:-1]
            
            similarity_scores = cosine_similarity(resume_vector, job_vectors).flatten()
            jobs['tfidf_score'] = similarity_scores * 100
            
        except Exception as e:
            print(f"TF-IDF calculation failed: {e}")
            jobs['tfidf_score'] = 0
        
        # Calculate skill match score
        resume_skills = self._extract_skills(resume)
        skill_scores = []
        
        for idx, row in jobs.iterrows():
            job_skills = row.get('skills', [])
            if isinstance(job_skills, list):
                # Calculate Jaccard similarity for skills
                if resume_skills and job_skills:
                    intersection = len(set(resume_skills) & set(job_skills))
                    union = len(set(resume_skills) | set(job_skills))
                    skill_score = (intersection / union * 100) if union > 0 else 0
                else:
                    skill_score = 0
            else:
                skill_score = 0
            
            skill_scores.append(skill_score)
        
        jobs['skill_score'] = skill_scores
        
        # Calculate overall score (weighted average)
        jobs['match_score'] = (jobs['tfidf_score'] * 0.6 + jobs['skill_score'] * 0.4).round(1)
        
        # Sort by match score
        matched_jobs = jobs.sort_values('match_score', ascending=False).head(top_n)
        
        return matched_jobs
    
    def _extract_skills(self, text: str) -> list:
        """Extract skills from text"""
        found_skills = []
        text_lower = text.lower()
        
        # Check for common skills
        for skill in self.common_skills:
            if skill in text_lower:
                found_skills.append(skill)
        
        # Also look for capitalized tech words (Python, Java, etc.)
        tech_words = re.findall(r'\b[A-Z][a-z]+\b', text)
        for word in tech_words:
            word_lower = word.lower()
            if word_lower in self.common_skills and word_lower not in found_skills:
                found_skills.append(word_lower)
        
        return list(set(found_skills))  # Remove duplicates
    
    def extract_keywords(self, text: str, top_k: int = 15) -> list:
        """Extract important keywords using TF-IDF"""
        try:
            # Simple word frequency approach
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            word_freq = {}
            
            for word in words:
                if word not in self.common_skills and len(word) > 2:
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Sort by frequency and get top keywords
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            keywords = [word for word, freq in sorted_words[:top_k]]
            
            # Add skills
            skills = self._extract_skills(text)
            all_keywords = list(set(keywords + skills))
            
            return all_keywords[:top_k]
            
        except Exception as e:
            print(f"Keyword extraction failed: {e}")
            return []