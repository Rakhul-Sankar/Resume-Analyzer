from django.contrib import admin
from django.contrib.auth.models import User
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html
from .models import ResumeReport
from .models import PasswordResetRequest


@admin.register(ResumeReport)
class ResumeReportAdmin(admin.ModelAdmin):

    list_display = (
        "get_user_name",
        "get_user_email",
        "resume_file",
        "colored_score",
        "analysis_status",
        "ats_rating",
        "analyzed_date",
        "reset_password_button",   # ⭐ NEW COLUMN
    )

    list_filter = ("analysis_status", "analyzed_date")
    search_fields = ("name", "user__first_name", "user__email")
    ordering = ("-analyzed_date",)
    readonly_fields = ("analyzed_date",)
    list_select_related = ("user",)

    # ---------- USER INFO ----------
    def get_user_name(self, obj):
        return obj.user.first_name or obj.user.username
    get_user_name.short_description = "User Name"

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = "Email"

    def resume_file(self, obj):
        return format_html("<b>{}</b>", obj.name)
    resume_file.short_description = "Resume File"

    # ---------- SCORE COLOR ----------
    def colored_score(self, obj):
        if obj.score >= 80:
            color = "green"
        elif obj.score >= 50:
            color = "orange"
        else:
            color = "red"
        return format_html('<b style="color:{};">{}%</b>', color, obj.score)
    colored_score.short_description = "ATS Score"

    # ---------- RESET PASSWORD BUTTON ----------
    def reset_password_button(self, obj):
        return format_html(
            '<a class="button" style="background:#dc2626;color:white;padding:4px 8px;border-radius:4px;" href="reset-password/{}/">Reset</a>',
            obj.user.id
        )
    reset_password_button.short_description = "🔑 Reset Password"

    # ---------- CUSTOM URL ----------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "reset-password/<int:user_id>/",
                self.admin_site.admin_view(self.reset_user_password),
                name="reset-user-password",
            ),
        ]
        return custom_urls + urls

    # ---------- RESET LOGIC ----------
    def reset_user_password(self, request, user_id):
        user = User.objects.get(id=user_id)
        new_password = "Temp@123"  # Default password
        user.set_password(new_password)
        user.save()

        self.message_user(
            request,
            f"Password reset for {user.username}. New password: {new_password}"
        )
        return redirect(request.META.get("HTTP_REFERER"))

@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "requested_at", "is_processed")
    list_filter = ("is_processed", "requested_at")
    search_fields = ("user__username", "user__email")
    ordering = ("-requested_at",)