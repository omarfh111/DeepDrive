# deals/forms.py
from django import forms
from .models import Partenariat

class PartenariatCreateForm(forms.ModelForm):
    class Meta:
        model = Partenariat
        fields = [
            "nom_societe", "email", "telephone",
            "nom_ceo", "date_partenariat",
            "detail_societe", "plafond",
        ]
        widgets = {
            "nom_societe": forms.TextInput(attrs={"class": "form-control-mod", "placeholder": "Nom de la société"}),
            "email": forms.EmailInput(attrs={"class": "form-control-mod", "placeholder": "ex: contact@societe.tn"}),
            "telephone": forms.TextInput(attrs={"class": "form-control-mod", "placeholder": "+216 55 555 555"}),
            "nom_ceo": forms.TextInput(attrs={"class": "form-control-mod", "placeholder": "Nom du CEO"}),
            "date_partenariat": forms.DateInput(attrs={"class": "form-control-mod", "type": "date"}),
            "detail_societe": forms.Textarea(attrs={"class": "form-control-mod", "rows": 4, "placeholder": "Activité, taille, notes…"}),
            "plafond": forms.NumberInput(attrs={"class": "form-control-mod", "step": "0.01", "min": "0"}),
        }

    # Ne PAS appeler .strip() si la valeur est None
    def clean(self):
        cleaned = super().clean()

        # champs texte optionnels -> normaliser (vider => None)
        for name in ["nom_societe", "email", "telephone", "nom_ceo", "detail_societe"]:
            v = cleaned.get(name)
            if v is None:
                cleaned[name] = None
            elif isinstance(v, str):
                v = v.strip()
                cleaned[name] = v or None

        # date_partenariat : si vide, on laisse le model remplir avec default=date.today
        if not cleaned.get("date_partenariat"):
            cleaned["date_partenariat"] = None

        return cleaned

    def clean_plafond(self):
        v = self.cleaned_data.get("plafond")
        if v in (None, ""):
            return None
        if v < 0:
            raise forms.ValidationError("Le plafond doit être positif.")
        return v
