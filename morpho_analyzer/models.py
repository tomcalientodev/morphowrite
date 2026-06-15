from django.db import models


from django.db import models

class CachedMorphoAnalysis(models.Model):
    """
    Acts as a high-speed performance shield, caching the complete linguistic 
    profile of a word—including its morphemes, grammatical roles, definition, 
    historical trivia, and real-world examples.
    """
    # The clean, lowercase version of the searched word acts as our lookup key
    word = models.CharField(max_length=100, unique=True, db_index=True)
    
    # Houses the entire structured JSON payload returned by Gemini
    analysis_data = models.JSONField()
    
    # Tracks when this analysis was first generated (perfect for tracking data age)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cached Morphological Analysis"
        verbose_name_plural = "Cached Morphological Analyses"

    def __str__(self):
        return self.word