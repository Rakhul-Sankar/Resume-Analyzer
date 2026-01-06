from django.db import models
from django.contrib.auth.models import User

class ResumeReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    score = models.IntegerField()
    analyzed_date = models.DateTimeField(auto_now_add=True)

    def status(self):
        if self.score >= 80:
            return "Excellent"
        elif self.score >= 60:
            return "Good"
        else:
            return "Needs Improvement"

    def __str__(self):
        return self.name
