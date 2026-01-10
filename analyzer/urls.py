from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),

    # Pages
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("upload/", views.upload_resume, name="upload"),
    path("analyze/", views.analyze_resume, name="analyze"),
    path("profile/", views.profile_view, name="profile"),

    # Reports
    path("reports/", views.reports_page, name="reports"),
    path("api/reports/", views.reports_api, name="reports_api"),
    path("api/reports/<int:report_id>/", views.delete_report, name="delete_report"),
]