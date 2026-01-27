from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
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
import re

from .models import ResumeReport


# =============================
# OPENROUTER CONFIG
# =============================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

OPENROUTER_MODELS = [
    "openai/gpt-4o-mini",        # ✅ Fast & always available
    "mistralai/mistral-7b-instruct",  # ✅ Good backup
]


print("OPENROUTER KEY LOADED:", bool(OPENROUTER_API_KEY))


# =============================
# LOCAL ATS (FALLBACK – ALWAYS WORKS)
# =============================

def local_ats_analysis(resume_text, job_description):
    resume_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", resume_text.lower()))
    jd_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", job_description.lower()))

    matched = sorted(resume_words & jd_words)
    missing = sorted(jd_words - resume_words)

    match_percentage = int((len(matched) / len(jd_words)) * 100) if jd_words else 0
    ats_score = min(match_percentage, 95)

    suggestions = (
        ["Improve skills and include more job-specific keywords."]
        if ats_score < 60
        else ["Your resume is well aligned with the job description."]
    )

    return {
        "ats_score": ats_score,
        "keyword_match_percentage": match_percentage,
        "matched_keywords": matched[:15],
        "missing_keywords": missing[:15],
        "improvement_suggestions": suggestions,
        "evaluation_mode": "local",
        "analysis_status": "Completed",
        "explanation": "ATS score calculated using local keyword-matching logic."
    }


# =============================
# JSON PARSER (SAFE)
# =============================

def safe_json_parse(text):
    try:
        text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == -1:
            return None
        return json.loads(text[start:end])
    except Exception:
        return None


# =============================
# AI ANALYSIS (WITH BACKUPS)
# =============================

def analyze_resume_text(resume_text, job_description):
    if not OPENROUTER_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "Referer": "http://localhost:8000",   # ✅ REQUIRED
        "X-Title": "AI Resume Analyzer"
    }

    prompt = f"""
Return ONLY valid JSON.

{{
  "ats_score": 0-100,
  "keyword_match_percentage": 0-100,
  "matched_keywords": [],
  "missing_keywords": [],
  "improvement_suggestions": []
}}

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}
"""

    for model in OPENROUTER_MODELS:
        try:
            print("🔍 Trying AI model:", model)

            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Return valid JSON only"},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                },
                timeout=25
            )

            if response.status_code != 200:
                print("❌ OpenRouter error:", response.status_code, response.text)
                continue

            content = response.json()["choices"][0]["message"]["content"]
            result = safe_json_parse(content)

            if (
                result
                and isinstance(result.get("ats_score"), (int, float))
                and result["ats_score"] > 0
                ):
                result["evaluation_mode"] = "ai"
                result["analysis_status"] = "Completed"
                result["explanation"] = "ATS score calculated using AI-based resume analysis."
                print("✅ AI RESULT ACCEPTED:", result["ats_score"])
                return result

        except Exception as e:
            print("❌ AI failed:", model, e)
            time.sleep(1)

    print("⚠️ AI unavailable → fallback to local ATS")
    return None


# =============================
# AUTH
# =============================
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password")

        if not email or not password:
            messages.error(request, "Please enter both email and password")
            return redirect("login")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        messages.error(request, "Invalid email or password")

    return render(request, "login.html")




def signup_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("signup")

        user = User.objects.create_user(
        username=email,
        email=email,
        first_name=name,
        password=password)
        # 🔥 tell Django which backend to use
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect("dashboard")

    return render(request, "signup.html")


def forgot_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("forgot_password")

        user = User.objects.filter(email=email).first()

        if not user:
            messages.error(request, "Email not registered")
            return redirect("forgot_password")

        user.set_password(new_password)
        user.save()


        messages.success(request, "Password updated successfully. Please login.")
        return redirect("login")

    return render(request, "forgot_password.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


# =============================
# DASHBOARD & PROFILE
# =============================

@login_required
def dashboard_view(request):
    hour = timezone.localtime().hour
    greeting = (
        "Good Morning" if hour < 12
        else "Good Afternoon" if hour < 16
        else "Good Evening"
    )
    return render(request, "dashboard.html", {"greeting": greeting})


@login_required
def profile_view(request):
    reports = ResumeReport.objects.filter(user=request.user).order_by("-analyzed_date")
    total_reports = reports.count()

    completed = reports.filter(analysis_status="Completed")
    avg_score = round(sum(r.score for r in completed) / completed.count(), 1) if completed else 0

    return render(request, "profile.html", {
        "reports": reports,
        "total_reports": total_reports,   # ✅ ADD THIS
        "avg_score": avg_score
    })



# =============================
# UPLOAD & ANALYZE
# =============================

@login_required
def upload_resume(request):
    return render(request, "upload.html")


def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    return " ".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_docx(file):
    return "\n".join(p.text for p in docx.Document(file).paragraphs)


@login_required
def analyze_resume(request):
    if request.method != "POST":
        return redirect("upload")

    resume = request.FILES.get("resume")
    job_description = request.POST.get("job_description")

    if resume.name.endswith(".pdf"):
        resume_text = extract_text_from_pdf(resume)
    elif resume.name.endswith(".docx"):
        resume_text = extract_text_from_docx(resume)
    else:
        messages.error(request, "Only PDF or DOCX supported.")
        return redirect("upload")

    # AI → Local fallback
    result = analyze_resume_text(resume_text, job_description)
    if not result:
        result = local_ats_analysis(resume_text, job_description)

    ResumeReport.objects.create(
        user=request.user,
        name=resume.name,
        score=result["ats_score"],
        analysis_status="Completed"
    )

    return render(request, "analyze.html", result)


# =============================
# REPORTS API
# =============================

@login_required
def reports_page(request):
    return render(request, "reports.html")


@login_required
def reports_api(request):
    reports = (
        ResumeReport.objects
        .filter(user=request.user)
        .order_by("-analyzed_date")
    )

    # Collect valid scores only
    scores = [r.score for r in reports if isinstance(r.score, (int, float))]

    total = len(scores)
    average = round(sum(scores) / total, 1) if total else 0
    best = max(scores) if total else 0

    return JsonResponse({
        "stats": {
            "total": total,
            "average": average,
            "best": best,
        },
        "reports": [
            {
                "id": r.id,
                "name": r.name,
                "score": r.score,
                "status": r.analysis_status,  # Completed / Pending
                "analyzed_date": timezone.localtime(
                    r.analyzed_date
                ).strftime("%d %b %Y, %I:%M %p")
            }
            for r in reports
        ]
    })


@login_required
def delete_report(request, report_id):
    ResumeReport.objects.filter(id=report_id, user=request.user).delete()
    return JsonResponse({"success": True})
