from django.db import models

class ScanHistory(models.Model):
    url = models.URLField()
    timestamp = models.DateTimeField(auto_now_add=True)
    summary = models.JSONField()

class Rule(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    guideline = models.TextField()
    severity = models.CharField(max_length=20)

    def __str__(self):
        return self.code