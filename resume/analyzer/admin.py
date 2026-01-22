from django.contrib import admin
from .models import ResumeReport


@admin.register(ResumeReport)
class ResumeReportAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "score", "analyzed_date", "status")
    search_fields = ("name", "user__username")
    list_filter = ("analyzed_date",)
    ordering = ("-analyzed_date",)
