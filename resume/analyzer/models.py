# models.py
from django.db import models
from django.contrib.auth.models import User

class ResumeReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    score = models.IntegerField()
    analyzed_date = models.DateTimeField(auto_now_add=True)

    def status(self):
        if self.score >= 85:
            return "Excellent"
        elif self.score >= 70:
            return "Good"
        elif self.score >= 50:
            return "Average"
        return "Poor"

    def __str__(self):
        return f"{self.name} ({self.score}%)"
