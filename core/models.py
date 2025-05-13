from django.db import models

# Create your models here.
class PsychiatricAnalysis(models.Model):
    session_id = models.CharField(max_length=64)
    timestamp = models.FloatField()
    emotion = models.CharField(max_length=32)
    anxiety_score = models.FloatField()
    depression_score = models.FloatField()
