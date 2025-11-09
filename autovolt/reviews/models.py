from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse


class Review(models.Model):
    """
    Model for reviews
    Based on UML diagram requirements:
    - id_Review (auto primary key)
    - Titre
    - Image
    - Description
    - DateReview (date)
    - date_joined (datetime)
    - Note
    """
    # Foreign Keys
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name="Utilisateur"
    )
    
    # Review Content - Matching UML diagram
    titre = models.CharField(
        max_length=200,
        verbose_name="Titre"
    )
    note = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name="Note",
        help_text="Note entre 0 et 5"
    )
    description = models.TextField(
        verbose_name="Description"
    )
    
    image = models.ImageField(
        upload_to='reviews/%Y/%m/%d/',
        verbose_name="Image",
        help_text="Upload an image for your review (optional)"
    )
    
    # Date fields - Matching UML diagram
    date_review = models.DateField(
        auto_now_add=True,
        verbose_name="DateReview"
    )
    date_joined = models.DateTimeField(
        auto_now_add=True,
        verbose_name="date_joined"
    )
    
    # Status
    is_approved = models.BooleanField(
        default=True,
        verbose_name="Approuvé",
        help_text="L'avis est-il visible publiquement?"
    )
    
    class Meta:
        ordering = ['-date_joined']
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
    
    def __str__(self):
        return f"{self.titre} - {self.user.username} ({self.note}⭐)"
    
    def get_absolute_url(self):
        return reverse('reviews:detail', kwargs={'pk': self.pk})
    
    @property
    def star_rating(self):
        """Returns star rating as full stars and half stars"""
        full_stars = int(self.note)
        half_star = 1 if (self.note - full_stars) >= 0.5 else 0
        empty_stars = 5 - full_stars - half_star
        return {
            'full': full_stars,
            'half': half_star,
            'empty': empty_stars
        }
    
    @property
    def id_Review(self):
        """Property to match UML diagram naming"""
        return self.id


class Commentaire(models.Model):
    """
    Model for comments on reviews
    Based on UML diagram requirements:
    - id_Commentaire (auto primary key)
    - Commentaire
    - DateCommentaire (date)
    """
    # Foreign Keys
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='commentaires',
        verbose_name="Avis"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='commentaires',
        verbose_name="Utilisateur"
    )
    
    # Comment Content - Matching UML diagram
    commentaire = models.TextField(
        verbose_name="Commentaire"
    )
    
    # Date field - Matching UML diagram
    date_commentaire = models.DateField(
        auto_now_add=True,
        verbose_name="DateCommentaire"
    )
    
    # Status
    is_approved = models.BooleanField(
        default=True,
        verbose_name="Approuvé"
    )
    
    class Meta:
        ordering = ['date_commentaire']
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"
    
    def __str__(self):
        return f"Commentaire de {self.user.username} sur {self.review.titre}"
    
    def get_absolute_url(self):
        return self.review.get_absolute_url()
    
    @property
    def id_Commentaire(self):
        """Property to match UML diagram naming"""
        return self.id