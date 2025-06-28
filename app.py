# (Keep your existing imports unchanged)
import base64
import json
import os
import random
import string
from datetime import timedelta

import fitz  # PyMuPDF
import googleapiclient.discovery
import googleapiclient.errors
import mysql.connector
import requests
from flask import Flask, render_template, redirect, request, session, url_for, flash
from mistralai import Mistral
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "Qazwsx@123")

# === Configuration ===
mistral_api_key = "WTuMOibXWmpTqjvscYHSaaCOjjXCakkJ"
mistral_model = "pixtral-large-2411"
ADZUNA_APP_ID = "b03f76e8"
ADZUNA_APP_KEY = "3aba17aaa08c6bd408d4f71350fa835a"
YOUTUBE_API_KEY = "AIzaSyBA_qmsRHzcID00CWOuQV6R5XBC4zrLe_Y"

# === Mistral Client Init ===
try:
    client = Mistral(api_key=mistral_api_key)
    print("Mistral client initialized")
except Exception as e:
    print(f"FATAL: Mistral init error: {e}")
    client = None

# === YouTube Init ===
try:
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    print("YouTube API client initialized")
except Exception as e:
    print(f"FATAL: YouTube init error: {e}")
    youtube = None

# === DB Connection ===
try:
    link = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='skillgap_2025'
    )
    print("DB connected")
except mysql.connector.Error as err:
    print(f"DB connection error: {err}")
    link = None

@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response

# === Helper Functions ===

def encode_image(image_filepath):
    try:
        with open(image_filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"Image encode error: {e}")
        return None

def pdf_to_images(pdf_filepath, output_folder):
    images = []
    try:
        doc = fitz.open(pdf_filepath)
        mat = fitz.Matrix(2, 2)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat)
            img_name = f"page_{i+1}.png"
            img_path = os.path.join(output_folder, img_name)
            pix.save(img_path)
            images.append(img_path)
        doc.close()
    except Exception as e:
        print(f"PDF conversion error: {e}")
    return images

def extract_keywords_from_image(image_path):
    if not client:
        return []
    image_base64 = encode_image(image_path)
    if not image_base64:
        return []

    prompt = (
        "Extract key skills, technologies, programming languages, frameworks, and job titles from this resume image. "
        "Return ONLY JSON like: {\"keywords\": [\"Python\", \"SQL\", \"AWS\"]}"
    )

    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": f"data:image/png;base64,{image_base64}"}
        ]
    }]

    try:
        response = client.chat.complete(
            model=mistral_model,
            messages=messages,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content).get("keywords", [])
    except Exception as e:
        print(f"Keyword extraction error: {e}")
        return []

def analyze_skill_gap(resume_skills, job_title):
    if not client:
        return {"missing_skills": [], "analysis": ""}
    prompt = (
        f"Compare resume skills: {resume_skills} with job title: {job_title}. "
        "Return JSON: {\"missing_skills\": [...], \"analysis\": \"...\"}"
    )

    try:
        response = client.chat.complete(
            model=mistral_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Skill gap error: {e}")
        return {"missing_skills": [], "analysis": ""}

def get_youtube_tutorials(keywords, total_videos=30):
    tutorials = {}
    if not youtube or not keywords:
        return tutorials

    num_keywords = len(keywords)
    per_keyword = max(1, total_videos // num_keywords)

    for keyword in keywords:
        try:
            search = youtube.search().list(
                q=f"{keyword} tutorial",
                part="id,snippet",
                maxResults=per_keyword,
                type="video"
            ).execute()
            tutorials[keyword] = [
                {
                    "title": i["snippet"]["title"],
                    "link": f"https://www.youtube.com/watch?v={i['id']['videoId']}"
                }
                for i in search.get("items", [])
            ]
        except Exception as e:
            print(f"YouTube API error ({keyword}): {e}")
    return tutorials

# === Routes ===

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('userhome'))
    return render_template('index.html')

@app.route('/ulogin', methods=['GET', 'POST'])
def ulogin():
    if request.method == 'GET':
        return render_template('ulogin.html')

    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        flash('All fields are required.', 'warning')
        return redirect(url_for('ulogin'))

    try:
        cursor = link.cursor(dictionary=True)
        cursor.execute("SELECT uid, name FROM skillgap_2025_user WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        if user:
            session['user'] = user['uid']
            session['username'] = user['name']
            session.permanent = True
            app.permanent_session_lifetime = timedelta(days=7)
            return redirect(url_for('userhome'))
        else:
            flash('Invalid credentials.', 'error')
    except Exception as e:
        print(f"Login DB error: {e}")
        flash('Server error occurred.', 'error')
    return render_template('ulogin.html')

@app.route('/uregister', methods=['GET', 'POST'])
def uregister():
    if request.method == 'GET':
        return render_template('uregister.html')

    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    phone = request.form.get("phone")

    if not all([name, email, password, phone]):
        flash('All fields required.', 'warning')
        return render_template('uregister.html')

    try:
        cursor = link.cursor()
        cursor.execute("SELECT email FROM skillgap_2025_user WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("User already exists. Please log in.", "error")
            return render_template('uregister.html')

        uid = "user_" + ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        cursor.execute("INSERT INTO skillgap_2025_user (uid, name, email, password, phone) VALUES (%s,%s,%s,%s,%s)",
                       (uid, name, email, password, phone))
        link.commit()
        flash('Registration successful!', 'success')
        return redirect(url_for('ulogin'))
    except Exception as e:
        print(f"Register DB error: {e}")
        flash('Registration failed.', 'error')
        return render_template('uregister.html')

@app.route('/userhome')
def userhome():
    if 'user' not in session:
        return redirect(url_for('ulogin'))
    return render_template('userhome.html', username=session['username'])

@app.route('/ulogout')
def ulogout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('ulogin'))

@app.route('/upload', methods=["GET", "POST"])
def upload():
    if 'user' not in session:
        return redirect(url_for('ulogin'))

    if request.method == "GET":
        return render_template('upload.html')

    job_title = request.form.get("job_designation")
    file = request.files.get('file')

    if not job_title or not file or file.filename == '':
        flash("Missing job title or file.", "error")
        return redirect(url_for('upload'))

    if not file.filename.lower().endswith('.pdf'):
        flash("Only PDF files are allowed.", "error")
        return redirect(url_for('upload'))

    filename = secure_filename(file.filename)
    uid = "proc_" + ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    work_dir = os.path.join("workspace", uid)
    pdf_path = os.path.join(work_dir, "pdf")
    img_path = os.path.join(work_dir, "images")
    os.makedirs(pdf_path, exist_ok=True)
    os.makedirs(img_path, exist_ok=True)

    file.save(os.path.join(pdf_path, filename))
    page_images = pdf_to_images(os.path.join(pdf_path, filename), img_path)

    keywords = set()
    for img in page_images:
        kw = extract_keywords_from_image(img)
        keywords.update(word.strip().title() for word in kw)

    resume_keywords = sorted(keywords)
    gap_analysis = analyze_skill_gap(resume_keywords, job_title)
    final_keywords = sorted(set(resume_keywords + gap_analysis.get("missing_skills", [])))

    job_results = []
    if ADZUNA_APP_ID != "YOUR_ADZUNA_APP_ID":
        search_terms = random.sample(final_keywords, min(5, len(final_keywords)))
        seen = set()
        for kw in search_terms:
            try:
                url = f"https://api.adzuna.com/v1/api/jobs/in/search/1?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}&what={kw}&where=bengaluru"
                res = requests.get(url, timeout=10)
                if res.ok:
                    for job in res.json().get("results", []):
                        job_id = job.get("id")
                        if job_id and job_id not in seen:
                            seen.add(job_id)
                            job_results.append(job)
                        if len(job_results) >= 5:
                            break
            except Exception as e:
                print(f"Adzuna error ({kw}): {e}")
            if len(job_results) >= 5:
                break

    tutorials = get_youtube_tutorials(final_keywords, total_videos=30)

    return render_template("upload.html",
                           success="Analysis completed successfully.",
                           job_results=job_results,
                           video_tutorials=tutorials,
                           keywords_found=final_keywords,
                           skill_gap_analysis=gap_analysis)

if __name__ == "__main__":
    os.makedirs("workspace", exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)