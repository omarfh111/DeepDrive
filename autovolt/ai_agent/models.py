from django.conf import settings
from django.db import models


class ResearchQuery(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="research_queries",
    )
    query = models.TextField()
    markdown_path = models.CharField(max_length=500, blank=True, null=True)
    html_path = models.CharField(max_length=500, blank=True, null=True)
    pdf_path = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} – {self.query[:50]}"
