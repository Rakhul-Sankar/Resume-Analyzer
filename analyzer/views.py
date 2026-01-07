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

        login(request, user)  # ✅ auto login
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
# DASHBOARD & PROFILE
# =============================

@login_required
def dashboard_view(request):
    hour = datetime.now().hour
    greeting = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 16 else "Good Evening"

    return render(request, "dashboard.html", {
        "greeting": greeting,
        "name": request.user.first_name
    })


@login_required
def profile_view(request):
    reports = ResumeReport.objects.filter(user=request.user)
    total = reports.count()
    avg = round(sum(r.score for r in reports) / total, 1) if total else 0

    return render(request, "profile.html", {
        "reports": reports,
        "total_reports": total,
        "avg_score": avg,
    })


# =============================
# RESUME
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


@login_required
def analyze_resume(request):
    if request.method == "POST":
        file = request.FILES.get("resume")

        if not file:
            return redirect("upload")

        text = extract_text_from_pdf(file) if file.name.endswith(".pdf") else extract_text_from_docx(file)
        skills = [s for s in SKILLS if s.lower() in text.lower()]
        score = int((len(skills) / len(SKILLS)) * 100)

        ResumeReport.objects.create(
            user=request.user,
            name=file.name,
            score=score
        )

        return render(request, "analyze.html", {
            "skills": skills,
            "score": score
        })

    return redirect("upload")


# =============================
# REPORTS
# =============================

@login_required
def reports_page(request):
    return render(request, "reports.html")


@login_required
def reports_api(request):
    reports = ResumeReport.objects.filter(user=request.user)
    return JsonResponse({
        "reports": [{
            "id": r.id,
            "name": r.name,
            "score": r.score,
            "status": r.status(),
            "analyzed_date": r.analyzed_date.strftime("%d %b %Y")
        } for r in reports]
    })


@login_required
def delete_report(request, report_id):
    ResumeReport.objects.filter(id=report_id, user=request.user).delete()
    return JsonResponse({"success": True})
