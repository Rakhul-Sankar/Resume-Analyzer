from django.contrib import admin
from .models import ResumeReport


@admin.register(ResumeReport)
class ResumeReportAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "name",
        "score",
        "analysis_status",
        "ats_rating",
        "analyzed_date",
    )

    list_filter = (
        "analysis_status",
        "analyzed_date",
    )

    search_fields = (
        "name",
        "user__username",
    )

    ordering = ("-analyzed_date",)

    readonly_fields = ("analyzed_date",)
