from django import forms
from .models import Service

class DustyFormMixin:
    """Ajoute les classes Bootstrap/Dusty aux widgets sans widget-tweaks/crispy."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            # Type date pour date_service
            if name == "date_service" and getattr(w, "input_type", "") != "date":
                if isinstance(w, forms.TextInput):
                    w.input_type = "date"
            # Classes CSS
            base = "form-select" if isinstance(w, (forms.Select, forms.SelectMultiple)) else "form-control"
            existing = w.attrs.get("class", "")
            w.attrs["class"] = f"{existing} {base}".strip()
            # Placeholders utiles
            if name == "nom_service":
                w.attrs.setdefault("placeholder", "Nom du service")
            if name == "description" and isinstance(w, forms.Textarea):
                w.attrs.setdefault("rows", 4)
                w.attrs.setdefault("placeholder", "Description détaillée (min 10 caractères)")
            if name == "type_service":
                w.attrs.setdefault("placeholder", "Type de service")

class ServiceForm(DustyFormMixin, forms.ModelForm):
    """Formulaire frontend - client assigné automatiquement"""
    class Meta:
        model = Service
        fields = [
            "nom_service", "description", "date_service", "statut", "type_service",
            "garantie", "type_vidange", "image"
        ]
        widgets = {
            "date_service": forms.DateInput(attrs={"type": "date"}),
            "statut": forms.Select(choices=[('', '-- Sélectionner --'), ('En attente', 'En attente'), ('En cours', 'En cours'), ('Terminé', 'Terminé')]),
            "type_service": forms.Select(choices=[('', '-- Sélectionner --'), ('Révision', 'Révision'), ('Vidange', 'Vidange'), ('Réparation', 'Réparation')]),
            "garantie": forms.Select(choices=[('', '-- Sélectionner --'), ('Sous garantie', 'Sous garantie'), ('Hors garantie', 'Hors garantie')]),
            "type_vidange": forms.Select(choices=[('', '-- Aucun --'), ('Huile moteur', 'Huile moteur'), ('Boîte de vitesse', 'Boîte de vitesse')]),
        }

    def clean_description(self):
        v = self.cleaned_data.get("description")
        if v and len(v.strip()) < 10:
            raise forms.ValidationError("La description doit faire au moins 10 caractères.")
        return v.strip() if v else None

    def clean(self):
        cleaned = super().clean()
        for name in ["nom_service", "description"]:
            v = cleaned.get(name)
            if isinstance(v, str):
                cleaned[name] = v.strip() or None
        return cleaned


class AdminServiceForm(DustyFormMixin, forms.ModelForm):
    """Formulaire backoffice - avec sélection du client"""
    
    client = forms.ModelChoiceField(
        queryset=None,  # Sera défini dans __init__
        label="Client",
        empty_label="-- Sélectionner un client --",
        widget=forms.Select(attrs={
            "class": "form-select",
        }),
        help_text="Sélectionnez le client pour qui vous créez ce service"
    )
    
    class Meta:
        model = Service
        fields = [
            "client", "nom_service", "description", "date_service", "statut", 
            "type_service", "garantie", "type_vidange", "image"
        ]
        widgets = {
            "date_service": forms.DateInput(attrs={"type": "date"}),
            "statut": forms.Select(choices=[('', '-- Sélectionner --'), ('En attente', 'En attente'), ('En cours', 'En cours'), ('Terminé', 'Terminé')]),
            "type_service": forms.Select(choices=[('', '-- Sélectionner --'), ('Entretien', 'Entretien'), ('Réparation', 'Réparation'), ('Diagnostic', 'Diagnostic'), ('Vidange', 'Vidange')]),
            "garantie": forms.Select(choices=[('', '-- Sélectionner --'), ('Sous garantie', 'Sous garantie'), ('Hors garantie', 'Hors garantie')]),
            "type_vidange": forms.Select(choices=[('', '-- Aucun --'), ('Huile moteur', 'Huile moteur'), ('Boîte de vitesse', 'Boîte de vitesse')]),
        }
        labels = {
            "nom_service": "Nom du service",
            "description": "Description",
            "date_service": "Date du service",
            "statut": "Statut",
            "type_service": "Type de service",
            "garantie": "Garantie",
            "type_vidange": "Type de vidange",
            "image": "Image (optionnelle)",
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Importer User ici pour éviter les imports circulaires
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Filtrer uniquement les clients (role='client') et trier par email
        self.fields['client'].queryset = User.objects.filter(role='client').order_by('email')
        
        # Personnaliser l'affichage: "Prénom Nom (email)" ou juste "email" si pas de nom
        def get_client_display(user):
            if user.first_name and user.last_name:
                return f"{user.first_name} {user.last_name} ({user.email})"
            elif user.first_name:
                return f"{user.first_name} ({user.email})"
            else:
                return user.email
        
        self.fields['client'].label_from_instance = get_client_display

    def clean_description(self):
        v = self.cleaned_data.get("description")
        if v and len(v.strip()) < 10:
            raise forms.ValidationError("La description doit faire au moins 10 caractères.")
        return v.strip() if v else None

    def clean(self):
        cleaned = super().clean()
        for name in ["nom_service", "description"]:
            v = cleaned.get(name)
            if isinstance(v, str):
                cleaned[name] = v.strip() or None
        return cleaned