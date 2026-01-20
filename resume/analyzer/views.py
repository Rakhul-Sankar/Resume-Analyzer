from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

import PyPDF2
import docx
import json
import requests
import os
import time

from .models import ResumeReport


# =============================
# OPENROUTER CONFIG
# =============================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-3.5-turbo"

print("OPENROUTER KEY LOADED:", bool(OPENROUTER_API_KEY))


# =============================
# AUTH
# =============================

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect("dashboard")

        messages.error(request, "Invalid email or password")

    return render(request, "login.html")


def signup_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(username=email).exists():
            messages.error(request, "User already exists")
            return redirect("signup")

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=name,
            password=password
        )

        login(request, user)
        return redirect("dashboard")

    return render(request, "signup.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        old = request.POST.get("old_password")
        new = request.POST.get("new_password")
        confirm = request.POST.get("confirm_password")

        if new != confirm:
            messages.error(request, "Passwords do not match")
            return redirect("forgot_password")

        try:
            user = User.objects.get(username=email)
        except User.DoesNotExist:
            messages.error(request, "User not found")
            return redirect("forgot_password")

        if not user.check_password(old):
            messages.error(request, "Old password incorrect")
            return redirect("forgot_password")

        user.set_password(new)
        user.save()

        messages.success(request, "Password updated. Please login.")
        return redirect("login")

    return render(request, "forgot_password.html")


# =============================
# DASHBOARD
# =============================

@login_required
def dashboard_view(request):
    hour = timezone.localtime().hour
    greeting = (
        "Good Morning" if hour < 12 else
        "Good Afternoon" if hour < 16 else
        "Good Evening"
    )

    return render(request, "dashboard.html", {
        "greeting": greeting,
        "name": request.user.first_name
    })


# =============================
# PROFILE
# =============================

@login_required
def profile_view(request):
    reports = ResumeReport.objects.filter(user=request.user).order_by("-analyzed_date")
    total_reports = reports.count()
    avg_score = round(sum(r.score for r in reports) / total_reports, 1) if total_reports else 0

    return render(request, "profile.html", {
        "reports": reports,
        "total_reports": total_reports,
        "avg_score": avg_score,
    })


# =============================
# UPLOAD PAGE
# =============================

@login_required
def upload_resume(request):
    return render(request, "upload.html")


# =============================
# FILE EXTRACTION
# =============================

def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    return " ".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_docx(file):
    document = docx.Document(file)
    return "\n".join(p.text for p in document.paragraphs)


# =============================
# OPENROUTER ANALYSIS
# =============================

def analyze_with_gpt(resume_text, job_description):

    if not OPENROUTER_API_KEY:
        raise Exception("OpenRouter API key not loaded")

    resume_text = resume_text[:2500]
    job_description = job_description[:800]

    prompt = f"""
Compare the RESUME with the JOB DESCRIPTION.

Return STRICT JSON ONLY:
{{
  "ats_score": number,
  "keyword_match_percentage": number,
  "matched_keywords": [],
  "missing_keywords": [],
  "explanation": "",
  "improvement_suggestions": []
}}

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Resume Analyzer Final Year Project"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert ATS resume evaluator."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    for _ in range(3):
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        print("OPENROUTER STATUS:", response.status_code)

        if response.status_code == 429:
            time.sleep(5)
            continue

        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(content[start:end])
            raise Exception("AI returned invalid JSON")

    raise Exception("AI is busy. Please wait 1 minute and try again.")


# =============================
# ANALYZE RESUME
# =============================

@login_required
def analyze_resume(request):
    if request.method != "POST":
        return redirect("upload")

    resume_file = request.FILES.get("resume")
    job_description = request.POST.get("job_description")

    if not resume_file or not job_description:
        messages.error(request, "Resume and Job Description are required")
        return redirect("upload")

    if resume_file.name.endswith(".pdf"):
        resume_text = extract_text_from_pdf(resume_file)
    elif resume_file.name.endswith(".docx"):
        resume_text = extract_text_from_docx(resume_file)
    else:
        messages.error(request, "Unsupported file format")
        return redirect("upload")

    if len(resume_text.strip()) < 100:
        messages.error(request, "Unable to read resume text.")
        return redirect("upload")

    try:
        ai_result = analyze_with_gpt(resume_text, job_description)
    except Exception as e:
        print("AI ANALYSIS ERROR:", e)
        messages.error(request, str(e))
        return redirect("upload")

    ResumeReport.objects.create(
        user=request.user,
        name=resume_file.name,
        score=ai_result["ats_score"]
    )

    return render(request, "analyze.html", ai_result)


# =============================
# REPORTS
# =============================

@login_required
def reports_page(request):
    return render(request, "reports.html")


@login_required
def reports_api(request):
    reports = ResumeReport.objects.filter(user=request.user).order_by("-analyzed_date")

    return JsonResponse({
        "reports": [
            {
                "id": r.id,
                "name": r.name,
                "score": r.score,
                "status": r.status(),
                "analyzed_date": timezone.localtime(r.analyzed_date).strftime("%d %b %Y, %I:%M %p")
            }
            for r in reports
        ]
    })


@login_required
def delete_report(request, report_id):
    ResumeReport.objects.filter(id=report_id, user=request.user).delete()
    return JsonResponse({"success": True})
