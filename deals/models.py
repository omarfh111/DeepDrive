from datetime import date
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


class Partenariat(models.Model):
    class Statut(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id_partenariat = models.AutoField(primary_key=True, db_column="id_partenariat")

    # 🔗 Liaison user
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="partenariat",
        db_column="user_id",
        null=True, blank=True  # facultatif pour ne pas bloquer la création
    )

    # 🧾 Champs sans valeurs par défaut
    nom_societe = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    nom_ceo = models.CharField(max_length=120, blank=True, null=True)
    date_partenariat = models.DateField(default=date.today)
    detail_societe = models.TextField(blank=True, null=True)

    plafond = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=9,
        choices=Statut.choices,
        default=Statut.PENDING,
        db_column="status",
    )

    class Meta:
        db_table = "partenariat"
        verbose_name = "Partenariat"
        verbose_name_plural = "Partenariats"

    def __str__(self):
        return self.nom_societe or "Partenariat sans nom"

    @property
    def plafond_effectif(self):
        return self.plafond or Decimal("0.00")
    def approve(self):
        self.status = self.Statut.APPROVED
        self.save(update_fields=["status"])

    def reject(self):
        self.status = self.Statut.REJECTED
        self.save(update_fields=["status"])
#Marhce
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
class Marche(models.Model):
    ETAT_CHOICES = [
        ('en_attente', 'En attente'),
        ('valide', 'Validé'),
        ('annule', 'Annulé'),
    ]

    partenaire = models.ForeignKey('deals.Partenariat', on_delete=models.CASCADE, related_name='marches')
    voiture = models.ForeignKey('vehicles.Voiture', on_delete=models.PROTECT, related_name='marches')

    quantite = models.PositiveIntegerField(default=1)
    # snapshot du prix de la voiture au moment de la création (pour figer le deal)
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=3)

    # calculés automatiquement
    total_prix = models.DecimalField(max_digits=14, decimal_places=3, editable=False)
    taux_rentabilite = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('10.00'),
        help_text="En %, appliqué sur le total (modifiable côté back si besoin)."
    )
    rentabilite_estime = models.DecimalField(max_digits=14, decimal_places=3, editable=False)

    etat = models.CharField(max_length=20, choices=ETAT_CHOICES, default='en_attente')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
            # vérifier que les FK sont posées sans toucher aux relations
            if not self.partenaire_id:
                raise ValidationError("Le partenaire est requis pour créer un marché.")
            if not self.voiture_id:
                raise ValidationError("La voiture est requise pour créer un marché.")
            if self.quantite is None or self.quantite <= 0:
                raise ValidationError("La quantité doit être positive.")
            if self.prix_unitaire is None:
                raise ValidationError("Le prix unitaire est requis.")

            # maintenant seulement on accède à l'objet partenaire (id est garanti)
            if getattr(self.partenaire, "status", None) != "approved":
                raise ValidationError("Votre partenariat doit être approuvé pour créer un marché.")

    def save(self, *args, **kwargs):
        # Calculs automatiques
        self.total_prix = (self.prix_unitaire or Decimal('0')) * Decimal(self.quantite or 0)
        taux = (self.taux_rentabilite or Decimal('0')) / Decimal('100')
        self.rentabilite_estime = (self.total_prix or Decimal('0')) * taux
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Marche #{self.id} - {self.partenaire} / {self.voiture} x{self.quantite}"