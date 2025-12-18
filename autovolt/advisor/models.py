from django.conf import settings
from django.db import models
from django.utils import timezone

class AdvisorAccess(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stripe_session_id = models.CharField(max_length=255, unique=True)
    active_until = models.DateTimeField()

    @property
    def is_active(self) -> bool:
        return timezone.now() < self.active_until

    def __str__(self):
        return f"AdvisorAccess(user={self.user_id}, until={self.active_until}, session={self.stripe_session_id})"
