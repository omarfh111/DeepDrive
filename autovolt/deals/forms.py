# deals/forms.py
from django import forms
from django.core.validators import RegexValidator
from .models import Partenariat, Marche


class DustyFormMixin:
    """Ajoute les classes Bootstrap/Dusty aux widgets sans widget-tweaks/crispy."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            # type date pour le champ date si pas déjà mis
            if name == "date_partenariat" and getattr(w, "input_type", "") != "date":
                if isinstance(w, forms.TextInput):
                    w.input_type = "date"
            # classes CSS
            base = "form-select" if isinstance(w, (forms.Select, forms.SelectMultiple)) else "form-control"
            existing = w.attrs.get("class", "")
            w.attrs["class"] = f"{existing} {base}".strip()
            # petits placeholders utiles
            if name == "nom_societe":
                w.attrs.setdefault("placeholder", "Nom de la société")
            if name == "email":
                w.attrs.setdefault("placeholder", "ex: contact@societe.tn")
            if name == "telephone":
                w.attrs.setdefault("placeholder", "+216 55 555 555")
            if name == "nom_ceo":
                w.attrs.setdefault("placeholder", "Nom du CEO")
            if name == "detail_societe" and isinstance(w, forms.Textarea):
                w.attrs.setdefault("rows", 4)


# =========================
#  FORM PARTENARIAT (FRONT)
# =========================
class PartenariatCreateForm(DustyFormMixin, forms.ModelForm):
    # On OVERRIDE certains champs du modèle pour les rendre obligatoires
    nom_societe = forms.CharField(
        label="Nom de la société",
        max_length=150,
        required=True,
        error_messages={
            "required": "Le nom de la société est obligatoire.",
        },
    )
    email = forms.EmailField(
        label="Email",
        required=True,
        error_messages={
            "required": "L’e-mail est obligatoire.",
            "invalid": "Veuillez saisir un e-mail valide.",
        },
    )
    telephone = forms.CharField(
        label="Téléphone",
        required=True,
        validators=[
            RegexValidator(
                regex=r"^\+216[0-9 ]{8,}$",
                message="Le numéro doit commencer par +216 et contenir au moins 8 chiffres.",
            )
        ],
        error_messages={
            "required": "Le téléphone est obligatoire.",
        },
    )
    nom_ceo = forms.CharField(
        label="Nom du CEO",
        required=True,
        error_messages={
            "required": "Le nom du CEO est obligatoire.",
        },
    )
    date_partenariat = forms.DateField(
        label="Date du partenariat",
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
        error_messages={
            "required": "La date du partenariat est obligatoire.",
        },
    )
    plafond = forms.DecimalField(
        label="Plafond (TND)",
        required=True,
        min_value=0,
        decimal_places=2,
        error_messages={
            "required": "Le plafond est obligatoire.",
            "min_value": "Le plafond doit être positif.",
        },
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
    )

    class Meta:
        model = Partenariat
        fields = [
            "nom_societe", "email", "telephone",
            "nom_ceo", "date_partenariat",
            "detail_societe", "plafond",
        ]

    def clean(self):
        cleaned = super().clean()

        # strip des strings
        for name in ["nom_societe", "email", "telephone", "nom_ceo", "detail_societe"]:
            v = cleaned.get(name)
            if isinstance(v, str):
                cleaned[name] = v.strip() or None

        # Vérif supplémentaire si besoin : date non vide (normalement géré par field.required)
        if not cleaned.get("date_partenariat"):
            self.add_error("date_partenariat", "La date du partenariat est obligatoire.")

        return cleaned

    def clean_plafond(self):
        v = self.cleaned_data.get("plafond")
        # min_value gère déjà le cas < 0, mais on ajoute un message au cas où
        if v is not None and v < 0:
            raise forms.ValidationError("Le plafond doit être positif.")
        return v


# =======================
#  FORM PARTENARIAT ADMIN
# =======================
class PartenariatAdminForm(DustyFormMixin, forms.ModelForm):
    class Meta:
        model = Partenariat
        fields = [
            "user", "nom_societe", "email", "telephone", "nom_ceo",
            "date_partenariat", "detail_societe", "plafond", "status",
        ]
        widgets = {
            "date_partenariat": forms.DateInput(attrs={"type": "date"}),
            "plafond": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def clean_plafond(self):
        v = self.cleaned_data.get("plafond")
        if v in (None, ""):
            return None
        if v < 0:
            raise forms.ValidationError("Le plafond doit être positif.")
        return v


# ==========
#  MARCHE
# ==========
class MarcheCreateForm(forms.ModelForm):
    class Meta:
        model = Marche
        fields = ["quantite"]
        widgets = {
            "quantite": forms.NumberInput(attrs={"min": 1, "class": "form-control-mod"})
        }

    def __init__(self, *args, **kwargs):
        self.voiture = kwargs.pop("voiture", None)
        self.partenaire = kwargs.pop("partenaire", None)
        super().__init__(*args, **kwargs)

    def clean_quantite(self):
        q = self.cleaned_data.get("quantite")
        if q is None or q <= 0:
            raise forms.ValidationError("La quantité doit être un entier positif.")
        return q

    def clean(self):
        cleaned = super().clean()

        # --- validations métier côté form ---
        if not self.partenaire:
            self.add_error(None, "Le partenaire est requis (et doit être approuvé).")
        if not self.voiture:
            self.add_error(None, "Aucune voiture sélectionnée.")
        elif self.voiture.prix is None:
            self.add_error(None, "Cette voiture n’a pas de prix défini.")

        # --- IMPORTANT : préparer l’instance AVANT _post_clean/full_clean ---
        self.instance.voiture = self.voiture
        self.instance.partenaire = self.partenaire
        self.instance.prix_unitaire = (self.voiture.prix if self.voiture else None)

        return cleaned

    def save(self, commit=True):
        # Ici tout est déjà posé sur self.instance
        obj = super().save(commit=False)
        if commit:
            obj.full_clean()  # ok maintenant avec quantite + contraintes modèle
            obj.save()
        return obj


class AdminMarcheForm(forms.ModelForm):
    class Meta:
        model = Marche
        fields = ["quantite", "taux_rentabilite", "etat"]
        widgets = {
            "quantite": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
            "taux_rentabilite": forms.NumberInput(attrs={"step": "0.01", "class": "form-control"}),
            "etat": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_quantite(self):
        q = self.cleaned_data.get("quantite")
        if q is None or q <= 0:
            raise forms.ValidationError("La quantité doit être positive.")
        return q
