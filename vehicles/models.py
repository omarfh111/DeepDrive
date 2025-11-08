from django.db import models

# Create your models here.

class Voiture(models.Model):
    CARROSSERIE_CHOICES = [
        ("berline", "Berline"),
        ("suv", "SUV"),
        ("citadine", "Citadine"),
        ("coupe", "Coupé"),
        ("break", "Break"),
        ("pickup", "Pick-up"),
        ("autre", "Autre"),
    ]
    ENERGY_CHOICES = [
        ("essence", "Essence"),
        ("diesel", "Diesel"),
        ("electrique", "Électrique"),
        ("hybride", "Hybride"),
        ("gpl", "GPL"),
        ("autre", "Autre"),
    ]
    BOITE_CHOICES = [
        ("manuelle", "Manuelle"),
        ("auto", "Automatique"),
    ]
    TRANSMISSION_CHOICES = [
        ("traction", "Traction"),
        ("propulsion", "Propulsion"),
        ("integrale", "Intégrale"),
    ]

    # Principaux champs
    marque = models.CharField(max_length=100)
    modele = models.CharField(max_length=100)
    annee  = models.PositiveIntegerField(null=True, blank=True)

    carrosserie = models.CharField(max_length=20, choices=CARROSSERIE_CHOICES, blank=True, null=True)
    nb_place    = models.PositiveSmallIntegerField(blank=True, null=True)
    nb_porte    = models.PositiveSmallIntegerField(blank=True, null=True)

    moteur          = models.CharField(max_length=100, blank=True, null=True)
    puissance_din   = models.FloatField(blank=True, null=True)
    puissance_fiscale = models.FloatField(blank=True, null=True)
    cylindre        = models.FloatField(blank=True, null=True)
    prix = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    energy        = models.CharField(max_length=20, choices=ENERGY_CHOICES, blank=True, null=True)
    boite_vitesse = models.CharField(max_length=20, choices=BOITE_CHOICES, blank=True, null=True)
    transmission  = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES, blank=True, null=True)

    # Libre-service pour attributs supplémentaires
    specs = models.JSONField(blank=True, null=True, help_text="Attributs libres (clé/valeur).")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.marque} {self.modele}".strip()