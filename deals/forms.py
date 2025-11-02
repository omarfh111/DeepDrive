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
