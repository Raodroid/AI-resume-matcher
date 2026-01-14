# test_quick.py
import pandas as pd
from job_api import JobSearchAPI
from job_matcher_simple import JobMatcher
import json

def quick_test():
    """Quick test to verify matching works"""
    print("🚀 Quick Test of Resume Matcher")
    print("=" * 50)
    
    # Sample resume
    resume_text = """
    SOFTWARE ENGINEER with 5 years of experience.
    
    SKILLS:
    - Python, JavaScript, TypeScript
    - React, Node.js, Express
    - AWS, Docker, Kubernetes
    - MongoDB, PostgreSQL, SQL
    - Git, CI/CD, Agile
    
    EXPERIENCE:
    Senior Software Engineer at TechCorp (3 years)
    - Developed scalable microservices using Python and Node.js
    - Implemented CI/CD pipelines with Docker and Kubernetes
    - Led team of 4 developers
    
    Software Developer at StartupCo (2 years)
    - Built full-stack web applications with React and Python
    - Implemented REST APIs and database design
    
    EDUCATION:
    B.S. Computer Science, University of Technology
    
    CERTIFICATIONS:
    AWS Certified Solutions Architect
    """
    
    # Create API instance (uses mock data by default)
    api = JobSearchAPI(use_mock=True)
    
    # Search for jobs
    print("\n1. Searching for jobs...")
    jobs = api.search_jobs("software engineer", "Remote", num_pages=1)
    print(f"   Found {len(jobs)} jobs")
    
    # Create matcher
    matcher = JobMatcher(use_weighted_matching=True)
    
    # Match resume to jobs
    print("\n2. Matching resume to jobs...")
    matches = matcher.match_resume_to_jobs(resume_text, jobs, top_n=5, min_score=40)
    
    if not matches.empty:
        print(f"   Found {len(matches)} matches")
        print("\n   Top Matches:")
        for idx, row in matches.iterrows():
            print(f"   - {row['job_title']} at {row['employer_name']}")
            print(f"     Match Score: {row['match_score']:.1f}%")
            print(f"     Remote: {row.get('remote_type', 'N/A')}")
            print(f"     Salary: {row.get('salary_display', 'Not specified')}")
            
            # Show matched skills
            try:
                job_skills = json.loads(row['skills']) if isinstance(row['skills'], str) else row['skills']
                print(f"     Skills: {', '.join(job_skills[:5])}")
            except:
                pass
            print()
        
        # Get insights
        print("\n3. Match Insights:")
        insights = matcher.get_match_insights(matches)
        if insights.get('top_skills_demanded'):
            print("   Top Skills in Demand:")
            for skill, count in insights['top_skills_demanded'][:5]:
                print(f"   - {skill}: {count} jobs")
        
        if insights.get('average_salary'):
            print(f"   Average Salary: {insights['average_salary']}")
        
        print(f"   Remote Jobs: {insights.get('remote_ratio', 0):.1f}%")
        
        # Gap analysis
        print("\n4. Resume Gap Analysis:")
        gap_analysis = matcher.generate_resume_gap_analysis(resume_text, matches)
        print(f"   Skills you have: {gap_analysis.get('strength_count', 0)}")
        print(f"   Skills to learn: {gap_analysis.get('missing_count', 0)}")
        if gap_analysis.get('missing_skills'):
            print("   Consider learning:")
            for skill in gap_analysis['missing_skills'][:5]:
                print(f"   - {skill}")
    
    else:
        print("❌ No matches found")
    
    print("\n" + "=" * 50)
    print("✅ Test completed successfully!")

if __name__ == "__main__":
    quick_test()