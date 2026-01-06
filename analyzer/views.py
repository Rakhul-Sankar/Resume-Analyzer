from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import datetime

import PyPDF2
import docx

from .models import ResumeReport


# =============================
# Authentication Views
# =============================

def login_page(request):
    return render(request, "login.html")


def signup_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters")
            return redirect("signup")

        if User.objects.filter(username=email).exists():
            messages.error(request, "User already exists with this email")
            return redirect("signup")

        User.objects.create_user(
            username=email,   # email as username
            email=email,
            first_name=name,
            password=password
        )

        messages.success(request, "Account created successfully. Please login.")
        return redirect("login")

    return render(request, "signup.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")  # email
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect("dashboard")

        messages.error(request, "Invalid email or password")

    return render(request, "login.html")


@login_required(login_url="login")
def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect("login")


# =============================
# Dashboard & Profile
# =============================

@login_required(login_url="login")
def dashboard_view(request):
    hour = datetime.now().hour

    greeting = (
        "Good Morning" if hour < 12 else
        "Good Afternoon" if hour < 16 else
        "Good Evening"
    )

    return render(request, "dashboard.html", {
        "greeting": greeting,
        "user": request.user,
    })


@login_required(login_url="login")
def profile_view(request):
    reports = ResumeReport.objects.filter(user=request.user)

    total = reports.count()
    avg = round(sum(r.score for r in reports) / total, 1) if total else 0

    return render(request, "profile.html", {
        "reports": reports,
        "total_reports": total,
        "avg_score": avg,
        "user": request.user,
    })


# =============================
# Resume Upload & Analysis
# =============================

@login_required(login_url="login")
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
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text()
    return text


def extract_text_from_docx(file):
    document = docx.Document(file)
    return "\n".join(p.text for p in document.paragraphs)


def find_skills(text):
    text = text.lower()
    return [skill for skill in SKILLS if skill.lower() in text]


def generate_suggestions(found_skills):
    missing = [s for s in SKILLS if s not in found_skills]
    return missing[:10] if missing else ["Great! You have included all key skills."]


def analyze_structure(text):
    text = text.lower()
    suggestions = []

    if not any(k in text for k in ["email", "@", "phone", "contact"]):
        suggestions.append("Add your contact information at the top.")

    if "education" not in text:
        suggestions.append("Include an Education section.")

    if "experience" not in text:
        suggestions.append("Add a Work Experience section.")

    if "skills" not in text:
        suggestions.append("Include a Skills section.")

    if "summary" not in text and "objective" not in text:
        suggestions.append("Add a Professional Summary or Objective.")

    if len(text.splitlines()) < 10:
        suggestions.append("Add more details for better structure.")

    return suggestions


@login_required(login_url="login")
def analyze_resume(request):
    if request.method == "POST":
        file = request.FILES.get("resume")

        if not file:
            return render(request, "upload.html", {
                "error": "Please upload a resume file"
            })

        if file.name.endswith(".pdf"):
            text = extract_text_from_pdf(file)
        elif file.name.endswith(".docx"):
            text = extract_text_from_docx(file)
        else:
            return render(request, "upload.html", {
                "error": "Unsupported file format"
            })

        skills_found = find_skills(text)
        ats_score = int((len(skills_found) / len(SKILLS)) * 100)

        ResumeReport.objects.create(
            user=request.user,
            name=file.name,
            score=ats_score
        )

        return render(request, "analyze.html", {
            "skills": skills_found,
            "score": ats_score,
            "structure_suggestions": analyze_structure(text),
            "skill_suggestions": generate_suggestions(skills_found)
        })

    return redirect("upload")


# =============================
# Reports
# =============================

@login_required(login_url="login")
def reports_page(request):
    return render(request, "reports.html")


@login_required(login_url="login")
def reports_api(request):
    reports = ResumeReport.objects.filter(user=request.user).order_by("-analyzed_date")

    return JsonResponse({
        "reports": [
            {
                "id": r.id,
                "name": r.name,
                "score": r.score,
                "status": r.status(),
                "analyzed_date": r.analyzed_date.strftime("%d %b %Y")
            }
            for r in reports
        ]
    })


@login_required(login_url="login")
def delete_report(request, report_id):
    if request.method == "POST":
        ResumeReport.objects.filter(
            id=report_id,
            user=request.user
        ).delete()
        return JsonResponse({"success": True})

    return JsonResponse({"success": False}, status=400)
