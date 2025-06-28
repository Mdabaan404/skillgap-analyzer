# SkillGap Analyzer

An intelligent web app that analyzes your resume, identifies missing skills for a target job role, and recommends learning resources and job listings. Built with Flask and powered by AI.

---

## Features

-  **Resume Upload** – Upload your resume in PDF format
-  **Skill Extraction** – Extracts key technologies, tools, and job roles from your resume using Mistral AI
-  **Skill Gap Analysis** – Compares your skills against a target job role and highlights missing skills
-  **Learning Resources** – Recommends YouTube tutorials for upskilling
-  **Job Matching** – Finds relevant job listings via Adzuna API
-  **User Login & Registration** – Secure and simple session-based authentication

---

##  Tech Stack

| Layer         | Technology                    |
|--------------|-------------------------------|
| Backend       | Python, Flask                  |
| Frontend      | HTML, CSS (Bootstrap), JS      |
| AI            | Mistral API (`pixtral-large-2411`) |
| Resume Parsing| PyMuPDF (fitz)                 |
| Video API     | YouTube Data API               |
| Job API       | Adzuna Job Search API          |
| Database      | MySQL                          |

---

##  Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Mdabaan404/skillgap-analyzer.git
cd skillgap-analyzer
