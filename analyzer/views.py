from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
import PyPDF2
import docx

# -----------------------------
# Authentication Views
# -----------------------------

def login_page(request):
    return render(request, 'login.html')

def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm")

        if password != confirm:
            messages.error(request, "Passwords do not match!")
            return redirect("signup")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return redirect("signup")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        user.save()
        messages.success(request, "Account created successfully!")
        return redirect("login")

    return render(request, "signup.html")   


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Invalid username or password")

    return render(request, "login.html")    


def dashboard_view(request):
    return render(request, "dashboard.html")  


def logout_view(request):
    logout(request)
    return redirect("login")  


# -----------------------------
# Resume Upload & Analysis Views
# -----------------------------
def upload_resume(request):
    return render(request, "upload.html")


# Skills list
SKILLS = [
    "Python", "Django", "Java", "JavaScript", "HTML", "CSS",
    "React", "Angular", "Node.js", "SQL", "MongoDB", "Web Development",
    "Machine Learning", "Data Analysis", "Git", "Docker", "AWS"
]


# Function to extract text from PDF
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text


# Function to extract text from DOCX
def extract_text_from_docx(file):
    document = docx.Document(file)
    return "\n".join([para.text for para in document.paragraphs])


# Function to find skills in resume text
def find_skills(text):
    found_skills = []
    text_lower = text.lower()
    for skill in SKILLS:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    return found_skills

# Function to generate missing skills suggestions
def generate_suggestions(found_skills):
    missing_skills = [skill for skill in SKILLS if skill not in found_skills]
    suggestions = []

    if missing_skills:
        suggestions.extend(missing_skills[:10])  # Show top 10 missing skills
    else:
        suggestions.append("Great! You have included all key skills.")

    return suggestions

# Analyze resume structure
def analyze_structure(text):
    suggestions = []
    text_lower = text.lower()

    if not any(word in text_lower for word in ["email", "@", "phone", "contact"]):
        suggestions.append("Add your contact information (email, phone) at the top.")
    if "education" not in text_lower:
        suggestions.append("Include an Education section with degrees, colleges, and years.")
    if "experience" not in text_lower and "work history" not in text_lower:
        suggestions.append("Add a Work Experience section detailing your roles and responsibilities.")
    if "skills" not in text_lower:
        suggestions.append("Include a Skills section to highlight your technical and soft skills.")
    if "summary" not in text_lower and "objective" not in text_lower:
        suggestions.append("Add a brief Professional Summary or Career Objective at the top.")
    if len(text.splitlines()) < 10:
        suggestions.append("Consider adding more details; a resume should be well-structured with multiple sections.")

    return suggestions

# Analyze resume view (without skill suggestions)
def analyze_resume(request):
    if request.method == "POST":
        file = request.FILES.get("resume")
        if not file:
            return render(request, "upload.html", {"error": "Please upload a file"})

        # Extract text from file
        if file.name.endswith(".pdf"):
            text = extract_text_from_pdf(file)
        else:
            text = extract_text_from_docx(file)

        # ATS score calculation based on found skills (optional)
        skills_found = find_skills(text)
        ats_score = int((len(skills_found) / len(SKILLS)) * 100)

        # Only analyze resume structure now
        structure_suggestions = analyze_structure(text)

        return render(request, "analyze.html", {
            "skills": skills_found,
            "score": ats_score,
            "structure_suggestions": structure_suggestions
        })

    return render(request, "upload.html")




