# deals/forms.py
from django import forms
from .models import Partenariat

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

class PartenariatCreateForm(DustyFormMixin, forms.ModelForm):
    class Meta:
        model = Partenariat
        fields = [
            "nom_societe", "email", "telephone",
            "nom_ceo", "date_partenariat",
            "detail_societe", "plafond",
        ]
        widgets = {
            "date_partenariat": forms.DateInput(attrs={"type": "date"}),
            "plafond": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def clean(self):
        cleaned = super().clean()
        for name in ["nom_societe", "email", "telephone", "nom_ceo", "detail_societe"]:
            v = cleaned.get(name)
            if isinstance(v, str):
                cleaned[name] = v.strip() or None
        if not cleaned.get("date_partenariat"):
            cleaned["date_partenariat"] = None
        return cleaned

    def clean_plafond(self):
        v = self.cleaned_data.get("plafond")
        if v in (None, ""): return None
        if v < 0: raise forms.ValidationError("Le plafond doit être positif.")
        return v

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
            # (les autres recevront leurs classes via DustyFormMixin)
        }

    def clean_plafond(self):
        v = self.cleaned_data.get("plafond")
        if v in (None, ""): return None
        if v < 0: raise forms.ValidationError("Le plafond doit être positif.")
        return v
#Marche

# deals/forms.py
from django import forms
from .models import Marche

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
            obj.full_clean()  # ok maintenant
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