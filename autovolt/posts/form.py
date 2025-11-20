from django import forms
from .models import Post


class DustyFormMixin:
    """
    Ajoute automatiquement les classes CSS du thème :
    - Inputs:   form-control form-control-mod
    - Selects:  form-select
    - Checkboxes: form-check-input
    - Fichiers: form-control (skinné)
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            w = field.widget

            # Choix de la classe de base selon le type de widget
            if isinstance(w, (forms.Select, forms.SelectMultiple)):
                base_classes = "form-select"
            elif isinstance(w, (forms.CheckboxInput,)):
                base_classes = "form-check-input"
            elif isinstance(w, (forms.FileInput, forms.ClearableFileInput)):
                base_classes = "form-control"  # input type="file"
            else:
                # TextInput, NumberInput, EmailInput, URLInput, DateInput, Textarea, etc.
                base_classes = "form-control form-control-mod"

            # Fusionner avec les classes existantes
            existing = w.attrs.get("class", "")
            w.attrs["class"] = (existing + " " + base_classes).strip()

            # Placeholders utiles
            placeholders = {
                "marque": "Marque (ex: Audi)",
                "modele": "Modèle (ex: RS7)",
                "year": "Année (ex: 2019)",
                "kilometrage": "Kilométrage (ex: 90000)",
                "energy": "Énergie (Essence / Diesel / Électrique / Hybride)",
                "boite_vitesse": "Boîte (Manuelle / Automatique)",
                "puissance_fiscale": "Puissance fiscale",
                "transmission": "Transmission (Traction / Propulsion / Intégrale)",
                "etat_general": "État général",
                "carrosserie": "Carrosserie (Berline, SUV...)",
                "nb_proprietes": "Nombre de propriétaires",
                "gouvernerat": "Gouvernorat",
                "price": "Prix en DT",
                "image": "Photo du véhicule",
            }
            if name in placeholders and not isinstance(w, forms.Select):
                w.attrs.setdefault("placeholder", placeholders[name])

            # Paramètres utiles sur les numériques
            if isinstance(field, forms.IntegerField):
                w.attrs.setdefault("step", "1")
                if name in {"year", "puissance_fiscale", "nb_proprietes"}:
                    w.attrs.setdefault("min", "0")
            if isinstance(field, forms.FloatField):
                w.attrs.setdefault("step", "0.01")
                if name in {"price", "kilometrage"}:
                    w.attrs.setdefault("min", "0")

            # Fichiers : accept images
            if isinstance(w, (forms.FileInput, forms.ClearableFileInput)):
                w.attrs.setdefault("accept", "image/*")


class PostForm(DustyFormMixin, forms.ModelForm):
    class Meta:
        model = Post
        exclude = ['owner','sold']
        fields = "__all__"
        # Widgets explicites pour forcer le rendering voulu
        widgets = {
            "year": forms.NumberInput(),
            "kilometrage": forms.NumberInput(),
            "puissance_fiscale": forms.NumberInput(),
            "nb_proprietes": forms.NumberInput(),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            # Utiliser FileInput (et non ClearableFileInput) pour éviter "Currently / Change"
            "image": forms.FileInput(attrs={"accept": "image/png",'required': True}),
        }
