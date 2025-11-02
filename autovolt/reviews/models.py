from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse

class Car(models.Model):
    """
    Placeholder Car model - UPDATE THIS with your actual Car model structure
    This is a temporary model to allow migrations to work.
    Replace this with your actual Car model when it's available.
    """
    name = models.CharField(max_length=200, verbose_name="Nom de la voiture")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Voiture"
        verbose_name_plural = "Voitures"
    
    def __str__(self):
        return self.name

class Review(models.Model):
    """
    Model for car reviews
    Based on your UML diagram and backlog requirements
    """
    # Foreign Keys
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name="Utilisateur"
    )
    # Note: You'll need to update 'Car' to match your actual car model name
    # Check with your car forum teammate what their model is called
    # It might be 'Voiture', 'Car', or 'Vehicle'
    car = models.ForeignKey(
        Car,  # Reference to Car model - update if your car model has a different name
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Voiture",
        null=True,  # Temporary - remove once you have the car model
        blank=True
    )
    
    # Review Content
    titre = models.CharField(
        max_length=200,
        verbose_name="Titre de l'avis"
    )
    note = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],
        verbose_name="Note",
        help_text="Note entre 0 et 5"
    )
    description = models.TextField(
        verbose_name="Description"
    )
    
    # Image (optional)
    image = models.ImageField(
        upload_to='reviews/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Image",
        help_text="Upload an image for your review (optional)"
    )
    
    # Timestamps
    date_review = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    date_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de modification"
    )
    
    # Status
    is_approved = models.BooleanField(
        default=True,
        verbose_name="Approuvé",
        help_text="L'avis est-il visible publiquement?"
    )
    
    class Meta:
        ordering = ['-date_review']
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
        # One review per user per car (only enforced when car is not null)
        # Note: Django's unique_together doesn't handle NULLs well, 
        # so we handle uniqueness in the view/form if car is optional
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'car'],
                condition=models.Q(car__isnull=False),
                name='unique_user_car_review'
            )
        ]
    
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


class Commentaire(models.Model):
    """
    Model for comments on reviews
    Based on your backlog - User Story 9
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
    
    # Comment Content
    commentaire = models.TextField(
        verbose_name="Commentaire"
    )
    
    # Timestamps
    date_commentaire = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    date_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="Date de modification"
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