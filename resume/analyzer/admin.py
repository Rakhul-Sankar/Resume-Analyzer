from django.contrib import admin
from django.utils.html import format_html
from .models import ResumeReport


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
    )

    list_filter = ("analysis_status", "analyzed_date")
    search_fields = ("name", "user__first_name", "user__email")
    ordering = ("-analyzed_date",)
    readonly_fields = ("analyzed_date",)
    list_select_related = ("user",)

    def get_user_name(self, obj):
        return obj.user.first_name or obj.user.username
    get_user_name.short_description = "User Name"

    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = "Email"

    def resume_file(self, obj):
        return format_html("<b>{}</b>", obj.name)
    resume_file.short_description = "Resume File"

    def colored_score(self, obj):
        if obj.score >= 80:
            color = "green"
        elif obj.score >= 50:
            color = "orange"
        else:
            color = "red"
        return format_html('<b style="color:{};">{}%</b>', color, obj.score)
    colored_score.short_description = "ATS Score"
