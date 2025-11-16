

# Create your models here.
from django.db import models
from django.conf import settings
from django.utils import timezone
from posts.models import Post

class Achat(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En cours"
        PAID = "paid", "Validé"
        CANCELED = "canceled", "Annulé"

    post = models.ForeignKey(
        Post,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='achats'
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='achats'
    )
    date_achat = models.DateTimeField(default=timezone.now)
    
    # Stripe fields
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)

    # Statut using TextChoices
    statut = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # snapshot du prix au moment de l’achat
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['-date_achat']

    def __str__(self):
        return f"Achat #{self.pk} – {self.post} – {self.buyer}"
    
    def save(self, *args, **kwargs):
        from decimal import Decimal
        if isinstance(self.price, float):
            self.price = Decimal(f"{self.price:.2f}")
        super().save(*args, **kwargs)

class Paiement(models.Model):
    METHOD_CHOICES = [
        ('card', 'Carte (Stripe)'),
        # you can add: ('cash', 'Espèces'), ('bank', 'Virement') later
    ]
    STATUS_CHOICES = [
        ('requires_payment', 'En attente'),
        ('succeeded', 'Réussi'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
    ]

    achat = models.ForeignKey('Achat', on_delete=models.CASCADE, related_name='paiements')
    methode_paiement = models.CharField(max_length=20, choices=METHOD_CHOICES, default='card')
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='requires_payment')
    date_paiement = models.DateTimeField(auto_now_add=True)

    # Stripe references
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Paiement #{self.id} - Achat #{self.achat_id} - {self.get_status_display()}"
    