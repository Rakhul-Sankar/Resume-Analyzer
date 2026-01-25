from django.db import models
from django.contrib.auth.models import User


class ResumeReport(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Completed", "Completed"),
        ("Failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    score = models.IntegerField(default=0)

    analysis_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    analyzed_date = models.DateTimeField(auto_now_add=True)

    def ats_rating(self):
        if self.analysis_status != "Completed":
            return "Pending"
        if self.score >= 85:
            return "Excellent"
        elif self.score >= 70:
            return "Good"
        elif self.score >= 50:
            return "Average"
        return "Poor"

    def __str__(self):
        return f"{self.name} | {self.analysis_status} | {self.score}%"
