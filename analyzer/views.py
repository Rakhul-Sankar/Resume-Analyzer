from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone

import PyPDF2
import docx

from .models import ResumeReport


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
    reports = ResumeReport.objects.filter(
        user=request.user
    ).order_by("-analyzed_date")

    total_reports = reports.count()
    avg_score = (
        round(sum(r.score for r in reports) / total_reports)
        if total_reports else 0
    )

    return render(request, "profile.html", {
        "reports": reports,
        "total_reports": total_reports,
        "avg_score": avg_score,
    })


# =============================
# RESUME ANALYSIS
# =============================

@login_required
def upload_resume(request):
    return render(request, "upload.html")


SKILLS = [
    "Python", "Django", "Java", "JavaScript", "HTML", "CSS",
    "React", "Angular", "Node.js", "SQL", "MongoDB",
    "Web Development", "Machine Learning", "Data Analysis",
    "Git", "Docker", "AWS"
]


def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    return " ".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_docx(file):
    document = docx.Document(file)
    return "\n".join(p.text for p in document.paragraphs)


def score_skills(text):
    found = [s for s in SKILLS if s.lower() in text]
    score = int((len(found) / len(SKILLS)) * 40)
    return score, found


def score_experience(text):
    keywords = ["experience", "intern", "project", "worked", "role"]
    return 30 if any(k in text for k in keywords) else 10


def score_education(text):
    keywords = ["education", "degree", "bachelor", "master", "college", "university"]
    return 20 if any(k in text for k in keywords) else 5


def score_structure(text):
    sections = ["skills", "education", "experience", "summary", "objective"]
    return min(sum(1 for s in sections if s in text) * 2, 10)


def analyze_structure(text):
    suggestions = []
    if "education" not in text:
        suggestions.append("Add an Education section.")
    if "experience" not in text:
        suggestions.append("Include a Work Experience section.")
    if "skills" not in text:
        suggestions.append("Mention a Skills section.")
    if "summary" not in text and "objective" not in text:
        suggestions.append("Add a Professional Summary or Objective.")
    return suggestions


def generate_suggestions(found_skills):
    missing = [s for s in SKILLS if s not in found_skills]
    return missing[:8]


@login_required
def analyze_resume(request):
    if request.method != "POST":
        return redirect("upload")

    file = request.FILES.get("resume")
    if not file:
        return redirect("upload")

    if file.name.endswith(".pdf"):
        text = extract_text_from_pdf(file)
    elif file.name.endswith(".docx"):
        text = extract_text_from_docx(file)
    else:
        messages.error(request, "Unsupported file format")
        return redirect("upload")

    text_lower = text.lower()

    # =============================
    # SECTION SCORES
    # =============================
    skill_score, skills_found = score_skills(text_lower)   # /40
    experience_score = score_experience(text_lower)        # /30
    education_score = score_education(text_lower)          # /20
    structure_score = score_structure(text_lower)          # /10

    # =============================
    # FINAL SCORE
    # =============================
    final_score = min(
        skill_score + experience_score + education_score + structure_score,
        100
    )

    # =============================
    # SAVE REPORT
    # =============================
    ResumeReport.objects.create(
        user=request.user,
        name=file.name,
        score=final_score
    )

    # =============================
    # PERCENTAGES FOR UI BARS
    # =============================
    skill_pct = int((skill_score / 40) * 100)
    experience_pct = int((experience_score / 30) * 100)
    education_pct = int((education_score / 20) * 100)
    structure_pct = int((structure_score / 10) * 100)

    # =============================
    # SEND EVERYTHING TO TEMPLATE
    # =============================
    return render(request, "analyze.html", {
        "score": final_score,

        # section scores
        "skill_score": skill_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "structure_score": structure_score,

        # percentages
        "skill_pct": skill_pct,
        "experience_pct": experience_pct,
        "education_pct": education_pct,
        "structure_pct": structure_pct,

        # data
        "skills": skills_found,
        "structure_suggestions": analyze_structure(text_lower),
        "skill_suggestions": generate_suggestions(skills_found),
    })


# =============================
# REPORTS
# =============================

@login_required
def reports_page(request):
    return render(request, "reports.html")


@login_required
def reports_api(request):
    reports = ResumeReport.objects.filter(
        user=request.user
    ).order_by("-analyzed_date")

    return JsonResponse({
        "reports": [
            {
                "id": r.id,
                "name": r.name,
                "score": r.score,
                "status": r.status(),
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