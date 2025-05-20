from flask import Flask, request, send_file
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import subprocess
import os
import re

app = Flask(__name__)
CORS(app)

UPDATED_RESUME_PATH = "updated_resume.tex"
PDF_OUTPUT_PATH = "updated_resume.pdf"

# Safely load OpenAI key from env var
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Missing OPENAI_API_KEY environment variable")

@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        data = request.get_json()
        job_url = data.get("job_url")
        print(f"Received job_url: {job_url}")

        if not job_url:
            return "Missing job_url", 400

        print(f"Scraping job posting from URL: {job_url}")
        job_title, job_text = get_full_job_posting(job_url)
        print(f"Scrape status: {'Success' if job_text else 'Fail'}")
        print(f"First 500 characters of job_text:\n{job_text[:500]}")

        if not job_text:
            return "Failed to scrape job posting", 500

        print("Starting extract_relevant_job_info...")
        job_description = extract_relevant_job_info(job_text)
        if not job_description:
            return "Failed to summarize job description", 500

        print("Reading base resume...")
        with open("base_resume.tex", "r", encoding="utf-8") as f:
            resume_text = f.read()

        print("Calling OpenAI to optimize resume...")
        optimized_resume = optimize_resume(resume_text, job_description)

        if not optimized_resume:
            return "Failed to optimize resume", 500

        optimized_resume = sanitize_latex_output(optimized_resume)

        with open(UPDATED_RESUME_PATH, "w", encoding="utf-8") as f:
            f.write(optimized_resume)

        print("Saved updated_resume.tex")

        print("Compiling LaTeX to PDF...")
        compile_result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", UPDATED_RESUME_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if compile_result.returncode != 0:
            print("PDF compilation failed:", compile_result.stderr.decode())
            return "PDF compilation failed", 500

        print("Returning generated PDF...")
        return send_file(
            PDF_OUTPUT_PATH,
            as_attachment=True,
            download_name="updated_resume.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        print("Exception occurred:", e)
        import traceback
        traceback.print_exc()
        return "Internal server error", 500


def get_full_job_posting(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, None
        soup = BeautifulSoup(response.text, 'html.parser')
        job_title = soup.title.string.strip() if soup.title else "Job Posting"
        job_text = soup.get_text(separator="\n").strip()
        return job_title, job_text
    except:
        return None, None


def extract_relevant_job_info(job_text):
    print("Sending prompt to OpenAI API...")
    prompt = f"""
    Extract the following details from this job posting:
    - Key Responsibilities
    - Required/Wanted Technical Skills
    - Relevant Background or Experience
    - Any other useful details for a resume.

    Job Posting:
    {job_text}
    """
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4-turbo",
            "messages": [
                {"role": "system", "content": "You are an expert at extracting job descriptions for resume building."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.3,
        },
    )
    print("OpenAI API status:", response.status_code)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    return None


def optimize_resume(resume_text, job_description):
    prompt = f"""
    Optimize and rewrite the following LaTeX resume to align with the job description.
    Do not remove LaTeX formatting.

    --- Resume ---
    {resume_text}

    --- Job Description ---
    {job_description}
    """
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4-turbo",
            "messages": [
                {"role": "system", "content": "You are an expert in LaTeX resume optimization."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000,
            "temperature": 0.5,
        },
    )
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    return None


def sanitize_latex_output(latex_text):
    """Remove ``` markers, extra markdown cruft, and trim."""
    latex_text = re.sub(r"^```latex\s*", "", latex_text.strip(), flags=re.IGNORECASE)
    latex_text = re.sub(r"```$", "", latex_text.strip())
    doc_index = latex_text.find(r"\documentclass")
    if doc_index != -1:
        latex_text = latex_text[doc_index:]
    return latex_text.strip()


if __name__ == "__main__":
    app.run(port=5000, debug=True)
