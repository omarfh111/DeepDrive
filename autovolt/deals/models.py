from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .emails import send_partner_status_email


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
        null=True,
        blank=True,  # facultatif pour ne pas bloquer la création
    )

    # 🧾 Infos société
    nom_societe = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    nom_ceo = models.CharField(max_length=120, blank=True, null=True)
    date_partenariat = models.DateField(default=date.today)
    detail_societe = models.TextField(blank=True, null=True)

    plafond = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0.00"))],
        blank=True,
        null=True,
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
        """Appelé depuis l’admin pour approuver le partenariat."""
        self.status = self.Statut.APPROVED
        self.save(update_fields=["status"])

    def reject(self):
        """Appelé depuis l’admin pour refuser le partenariat."""
        self.status = self.Statut.REJECTED
        self.save(update_fields=["status"])


# ==== SIGNALS PARTENARIAT ====


@receiver(pre_save, sender=Partenariat)
def _flag_status_change(sender, instance, **kwargs):
    """
    Marque sur l'instance si le statut va changer pour 'approved' ou 'rejected'
    afin d'envoyer l'email après sauvegarde.
    """
    if not instance.pk:
        # Création : si on crée directement en approved/rejected
        instance._send_status_mail = instance.status in (
            instance.Statut.APPROVED,
            instance.Statut.REJECTED,
        )
        return

    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._send_status_mail = instance.status in (
            instance.Statut.APPROVED,
            instance.Statut.REJECTED,
        )
        return

    instance._send_status_mail = (
        old.status != instance.status
        and instance.status in (instance.Statut.APPROVED, instance.Statut.REJECTED)
    )


@receiver(post_save, sender=Partenariat)
def _send_status_change_email(sender, instance, **kwargs):
    """
    1) Envoie l'e-mail de statut (approved / rejected)
    2) Si APPROVED, lance le pipeline de reco + e-mail de recommandation.
    """
    if getattr(instance, "_send_status_mail", False):
        # 1️⃣ Email "Votre partenariat a été approuvé / refusé"
        send_partner_status_email(instance)

        # 2️⃣ Si APPROVED -> lancer le moteur de recommandation
        if instance.status == instance.Statut.APPROVED:
            try:
                # import paresseux pour éviter les imports circulaires
                from .recommendation import run_recommendation_pipeline

                run_recommendation_pipeline(instance)
            except Exception as e:
                print("Erreur pipeline de recommandation :", e)

        # Nettoyage du flag
        try:
            delattr(instance, "_send_status_mail")
        except Exception:
            pass


# ==== MARCHE ====


class Marche(models.Model):
    ETAT_CHOICES = [
        ("en_attente", "En attente"),
        ("valide", "Validé"),
        ("annule", "Annulé"),
    ]

    partenaire = models.ForeignKey(
        "deals.Partenariat",
        on_delete=models.CASCADE,
        related_name="marches",
    )
    voiture = models.ForeignKey(
        "vehicles.Voiture",
        on_delete=models.PROTECT,
        related_name="marches",
    )

    quantite = models.PositiveIntegerField(default=1)
    # snapshot du prix de la voiture au moment de la création (pour figer le deal)
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=3)

    # calculés automatiquement
    total_prix = models.DecimalField(max_digits=14, decimal_places=3, editable=False)
    taux_rentabilite = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        help_text="En %, appliqué sur le total (modifiable côté back si besoin).",
    )
    rentabilite_estime = models.DecimalField(
        max_digits=14, decimal_places=3, editable=False
    )

    etat = models.CharField(
        max_length=20, choices=ETAT_CHOICES, default="en_attente"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        field_errors = {}
        non_field_errors = []

        # champ présent dans le formulaire -> erreur ciblée OK
        if self.quantite is not None and self.quantite <= 0:
            field_errors["quantite"] = "La quantité doit être positive."

        # ces champs NE sont PAS dans le formulaire -> erreurs globales
        if self.prix_unitaire is None:
            non_field_errors.append("Le prix unitaire est requis.")
        if self.partenaire_id and getattr(self.partenaire, "status", None) != "approved":
            non_field_errors.append(
                "Votre partenariat doit être approuvé pour créer un marché."
            )
        if self.voiture_id is None:
            non_field_errors.append("La voiture est requise pour créer un marché.")

        # 🔹 Coût total + comparaison au plafond 🔹
        if self.partenaire_id and self.prix_unitaire is not None and self.quantite is not None:
            total = (self.prix_unitaire or Decimal("0")) * Decimal(self.quantite or 0)
            plafond = getattr(self.partenaire, "plafond_effectif", None) or Decimal("0.00")

            if plafond > Decimal("0.00") and total > plafond:
                non_field_errors.append(
                    f"Le coût total du marché ({total} TND) dépasse le plafond autorisé ({plafond} TND)."
                )

        if field_errors and non_field_errors:
            raise ValidationError({**field_errors, "__all__": non_field_errors})
        if field_errors:
            raise ValidationError(field_errors)
        if non_field_errors:
            raise ValidationError(non_field_errors)

    def save(self, *args, **kwargs):
        # Calculs automatiques
        self.total_prix = (self.prix_unitaire or Decimal("0")) * Decimal(
            self.quantite or 0
        )
        taux = (self.taux_rentabilite or Decimal("0")) / Decimal("100")
        self.rentabilite_estime = (self.total_prix or Decimal("0")) * taux
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Marche #{self.id} - {self.partenaire} / {self.voiture} x{self.quantite}"

    @property
    def depasse_plafond(self):
        if not self.partenaire_id:
            return False
        plafond = self.partenaire.plafond_effectif
        if plafond <= Decimal("0.00"):
            return False
        return self.total_prix > plafond