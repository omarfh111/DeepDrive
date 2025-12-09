
from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator
from datetime import date
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.db.models.signals import pre_save, post_save  # ← Ajouté
from django.dispatch import receiver       
from .emails import send_service_status_email


STATUT_CHOICES = [
    ('En attente', 'En attente'),
    ('En cours', 'En cours'),
    ('Terminé', 'Terminé'),
    ('Annulé', 'Annulé'),
]

TYPE_SERVICE_CHOICES = [
    ('Entretien', 'Entretien'),
    ('Réparation', 'Réparation'),
    ('Diagnostic', 'Diagnostic'),
    ('Vidange', 'Vidange'),
]

TYPE_VIDANGE_CHOICES = [
    ('Huile moteur', 'Huile moteur'),
    ('Boîte de vitesse', 'Boîte de vitesse'),
]

GARANTIE_CHOICES = [
    ('Sous garantie', 'Sous garantie'),
    ('Hors garantie', 'Hors garantie'),
]

class Service(models.Model):

    client = models.ForeignKey(           
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name="Client"
    )
    
    nom_service = models.CharField(
        max_length=100,
        unique=True,
        validators=[
            RegexValidator(r'^[a-zA-Z\s]+$', 'Le nom ne doit contenir que des lettres et espaces.'),
        ]
    )
    description = models.TextField(
        validators=[
            MinLengthValidator(10, 'La description doit faire au moins 10 caractères.'),
            MaxLengthValidator(500, 'La description ne peut pas dépasser 500 caractères.'),
        ]
    )
    date_service = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES)
    garantie = models.CharField(max_length=50, choices=GARANTIE_CHOICES)
    type_service = models.CharField(max_length=50, choices=TYPE_SERVICE_CHOICES)
    type_vidange = models.CharField(
        max_length=50, 
        choices=TYPE_VIDANGE_CHOICES,
        blank=True, 
        null=True
    )
    image = models.ImageField(upload_to='media_service/', blank=True, null=True)

    def clean(self):
        # Vérifie que date_service est dans le futur
        if self.date_service is not None:
            if self.date_service <= timezone.localdate():
                raise ValidationError("La date du service doit être dans le futur.")
                
    def __str__(self):
        return self.nom_service
    






    
# ============================================
# SIGNAUX POUR ENVOI D'EMAILS
# ============================================


@receiver(pre_save, sender=Service)
def _flag_service_status_change(sender, instance, **kwargs):
    """
    Marque sur l'instance si le statut va changer pour 'Terminé' ou 'Annulé'
    afin d'envoyer l'email après sauvegarde.
    """
    # Si c'est une nouvelle instance (pas encore en DB)
    if not instance.pk:
        instance._send_status_mail = instance.statut in ('Terminé', 'Annulé')
        return
    
    # Récupérer l'ancienne version depuis la DB
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._send_status_mail = instance.statut in ('Terminé', 'Annulé')
        return

    # Vérifier si le statut a changé vers 'Terminé' ou 'Annulé'
    instance._send_status_mail = (
        old.statut != instance.statut and
        instance.statut in ('Terminé', 'Annulé')
    )


@receiver(post_save, sender=Service)
def _send_service_status_email(sender, instance, **kwargs):
    """
    Envoie l'email seulement si le flag a été posé en pre_save.
    """
    if getattr(instance, "_send_status_mail", False):
        send_service_status_email(instance)  # ← CORRECT : appelle la fonction d'emails.py
        try:
            delattr(instance, "_send_status_mail")
        except Exception:
            pass














































