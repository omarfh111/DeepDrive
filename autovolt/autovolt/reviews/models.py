# reviews/models.py
from django.db import models
from django.conf import settings                        # ✅ use the swapped user model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse


class Review(models.Model):
    user = models.ForeignKey(                           # ✅ point to AUTH_USER_MODEL
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Utilisateur"
    )
    titre = models.CharField(max_length=200, verbose_name="Titre")
    note = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name="Note",
        help_text="Note entre 0 et 5"
    )
    description = models.TextField(verbose_name="Description")
    image = models.ImageField(upload_to='reviews/%Y/%m/%d/', verbose_name="Image")
    date_review = models.DateField(auto_now_add=True, verbose_name="DateReview")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="date_joined")
    is_approved = models.BooleanField(default=True, verbose_name="Approuvé")

    class Meta:
        ordering = ['-date_joined']
        verbose_name = "Avis"
        verbose_name_plural = "Avis"

    def __str__(self):
        # your custom user has no username field → show email or full name
        display = self.user.email or f"{self.user.first_name} {self.user.last_name}".strip()
        return f"{self.titre} - {display} ({self.note}⭐)"

    def get_absolute_url(self):
        return reverse('reviews:detail', kwargs={'pk': self.pk})

    @property
    def star_rating(self):
        full = int(self.note)
        half = 1 if (self.note - full) >= 0.5 else 0
        empty = 5 - full - half
        return {'full': full, 'half': half, 'empty': empty}

    @property
    def id_Review(self):
        return self.id


class Commentaire(models.Model):
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='commentaires',
        verbose_name="Avis"
    )
    user = models.ForeignKey(                           # ✅ point to AUTH_USER_MODEL
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='commentaires',
        verbose_name="Utilisateur"
    )
    commentaire = models.TextField(verbose_name="Commentaire")
    date_commentaire = models.DateField(auto_now_add=True, verbose_name="DateCommentaire")
    is_approved = models.BooleanField(default=True, verbose_name="Approuvé")

    class Meta:
        ordering = ['date_commentaire']
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"

    def __str__(self):
        display = self.user.email or f"{self.user.first_name} {self.user.last_name}".strip()
        return f"Commentaire de {display} sur {self.review.titre}"

    def get_absolute_url(self):
        return self.review.get_absolute_url()

    @property
    def id_Commentaire(self):
        return self.id
