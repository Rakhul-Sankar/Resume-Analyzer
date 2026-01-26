from django.urls import path
from django.shortcuts import redirect
from . import views

# Home redirect logic (PROFESSIONAL METHOD)
def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


urlpatterns = [
    # Root path
    path('', home_redirect, name='home'),

    # Authentication
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),

    # Main Pages
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("upload/", views.upload_resume, name="upload"),
    path("analyze/", views.analyze_resume, name="analyze"),
    path("profile/", views.profile_view, name="profile"),

    # Reports
    path("reports/", views.reports_page, name="reports"),
    path("api/reports/", views.reports_api, name="reports_api"),
    path("api/reports/<int:report_id>/", views.delete_report, name="delete_report"),
]
