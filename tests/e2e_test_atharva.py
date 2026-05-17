"""
tests/e2e_test_atharva.py
-------------------------
End-to-End test using Atharva Vavhal's resume text extracted from the provided image.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.preprocessor import preprocess
from core.scorer import compute_score, get_missing_skills
from core.skill_extractor import extract_skills

# 1. Atharva's Resume Text (Extracted from image)
RESUME_TEXT = """
ATHARVA VAVHAL
+91 86006 97250 | atharvavavhal@gmail.com | linkedin.com/in/atharva-vavhal | github.com/atharvavavhal
leetcode.com/atharvavavhal

EDUCATION
Vishwakarma Institute of Technology, Expected May 2029
Bachelor of Technology in Computer Engineering, Pune, Maharashtra
Relevant Coursework: Data Structures & Algorithms, DBMS, OOP, Operating Systems

TECHNICAL SKILLS
Languages: C++, JavaScript (ES6+), Python
Frontend: React.js, Next.js, TypeScript, HTML5, CSS3
Backend: Node.js, Express.js, REST API Design, Socket.io
Databases: MongoDB, MySQL, Mongoose ODM
Tools & Infra: Git, GitHub, Vercel, Postman, Linux CLI
CS Concepts: Data Structures & Algorithms, System Design, MVC, JWT Auth, TCP/IP

PROJECTS
AI Resume Analyzer
Node.js, Express.js, React.js, OpenAI API, MongoDB
- Built a full-stack resume analysis tool using OpenAI's Chat Completions API; processes PDF uploads server-side, extracts text,
and returns structured, category-level feedback in under 3 seconds end-to-end.
- Engineered a PDF ingestion pipeline handling multipart uploads with token-optimised prompts — keeping API costs below $0.02
per analysis by chunking and truncating input intelligently.
- Designed a React dashboard with categorised feedback panels (Skills, Experience, Impact) enabling users to act on AI output
without reading raw JSON — improved usability in self-tested sessions.

MERN Task Manager
MongoDB, Express.js, React.js, Node.js, JWT, bcrypt
- Implemented stateless JWT authentication with bcrypt-hashed passwords; all 12+ protected API routes verified via a single
reusable Express middleware, reducing auth logic duplication by 100%.
- Designed a RESTful API with resource-oriented routing, centralised error handling, and schema-level validation via Mongoose —
eliminated all inconsistent 500 responses across endpoints.
- Optimised React state management to support real-time task filtering, priority reordering, and status updates with zero full-
page reloads, using component-level state and memoised selectors.

Real-Time Chat Application
Node.js, Socket.io, Express.js, HTML5, CSS3
- Built a multi-room WebSocket messaging system supporting 50+ concurrent connections with isolated room namespaces,
preventing cross-room data leakage at the event-routing layer.
- Modelled the full connection lifecycle (handshake -> room join -> broadcast -> disconnect) as a clean event graph in Socket.io,
keeping all stateful logic in a single 120-line server module.
- Delivered a mobile-first frontend with optimistic UI updates: messages appear instantly client-side while Socket.io confirms
delivery asynchronously, giving sub-50ms perceived latency.

COMPETITIVE PROGRAMMING & OPEN SOURCE
- Solved 150+ problems on LeetCode across arrays, trees, graphs, and dynamic programming — targeting 300+ problems and a
LeetCode rating of 1600+ within 6 months.
- Actively practicing Codeforces Div. 3 rounds to build algorithmic speed and pattern recognition for technical interview
preparation.
- All personal projects are open-source on GitHub with structured README documentation, commit history, and issue tracking to
simulate a professional engineering workflow.

ADDITIONAL
- Proficient in Git branching workflows (feature branches, PRs, atomic commits) — all projects versioned on GitHub with
descriptive commit history.
- Actively studying backend system design concepts: load balancing, caching strategies, database indexing, and horizontal scaling
patterns.
- Seeking backend/full-stack SWE internship roles for Summer 2026; open to open-source contributions in Node.js/React
ecosystems.
"""

# 2. Target Job Description (MERN/Full-Stack Developer)
JD_TEXT = """
We are looking for a Full Stack Developer (MERN) with strong experience in 
Node.js, Express.js, and React.js. 

Key Requirements:
- Proficiency in JavaScript and TypeScript.
- Hands-on experience with MongoDB and Mongoose.
- Experience building RESTful APIs and real-time features using Socket.io.
- Familiarity with JWT authentication and secure backend design.
- Knowledge of Data Structures & Algorithms.
- Strong Git and GitHub skills.
- Experience with Next.js is a plus.
"""

def run_e2e_test():
    print("=" * 60)
    print(" HIREMATCH END-TO-END TEST: ATHARVA VAVHAL")
    print("=" * 60)

    # A. Preprocessing
    print("\n[1] Preprocessing...")
    clean_resume = preprocess(RESUME_TEXT)
    clean_jd = preprocess(JD_TEXT)
    print(f"    Resume words: {len(clean_resume.split())}")
    print(f"    JD words:     {len(clean_jd.split())}")

    # B. Skill Extraction
    print("\n[2] Extracting Skills...")
    resume_extracted = extract_skills(RESUME_TEXT)
    jd_extracted = extract_skills(JD_TEXT)
    
    resume_skills = set(resume_extracted["all_skills"])
    jd_skills = set(jd_extracted["all_skills"])
    
    matched = sorted(resume_skills & jd_skills)
    missing = sorted(jd_skills - resume_skills)
    
    print(f"    Matched Skills ({len(matched)}): {', '.join(matched)}")
    print(f"    Missing Skills ({len(missing)}): {', '.join(missing) or 'None! Perfect match.'}")

    # C. Scoring
    print("\n[3] Computing Match Score...")
    score_result = compute_score(clean_resume, clean_jd)
    
    print(f"\n    MATCH SCORE: {score_result.score}%")
    print(f"    MATCH LEVEL: {score_result.label}")
    print(f"    COSINE RAW : {score_result.cosine_raw}")

    print("\n" + "=" * 60)
    print(" TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_e2e_test()
