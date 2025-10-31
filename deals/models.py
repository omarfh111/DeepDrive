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
