from django import forms
from .models import Review, Commentaire
from .content_validator import validate_content   # ← updated import (LLM validator)


# ============================
# Review Form
# ============================
class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['titre', 'note', 'description', 'image']
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de votre avis',
                'required': True
            }),
            'note': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '5',
                'step': '0.5',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Décrivez votre expérience (positivement et avec bienveillance)...',
                'required': True
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
        labels = {
            'titre': 'Titre de l\'avis',
            'note': 'Note (0-5 étoiles)',
            'description': 'Votre avis positif',
            'image': 'Image (facultative)'
        }
        help_texts = {
            'note': 'Donnez une note entre 0 et 5 étoiles.',
            'description': 'Votre message doit être positif et constructif.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].required = False


    # --- POSITIVE-ONLY VALIDATION USING LLM ---
    def clean_description(self):
        text = self.cleaned_data.get('description')

        if len(text) < 50:
            raise forms.ValidationError("Votre avis doit contenir au moins 50 caractères.")

        allowed, msg = validate_content(text)
        if not allowed:
            raise forms.ValidationError(msg)

        return text


    def clean_titre(self):
        titre = self.cleaned_data.get('titre')

        allowed, msg = validate_content(titre)
        if not allowed:
            raise forms.ValidationError(msg)

        return titre


    def clean_note(self):
        note = self.cleaned_data.get('note')

        if note < 0 or note > 5:
            raise forms.ValidationError("La note doit être entre 0 et 5.")

        return note



# ============================
# Comment Form
# ============================
class CommentaireForm(forms.ModelForm):
    class Meta:
        model = Commentaire
        fields = ['commentaire']
        widgets = {
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ajoutez un commentaire positif...',
                'required': True
            })
        }

    def clean_commentaire(self):
        commentaire = self.cleaned_data.get('commentaire')

        if len(commentaire) < 10:
            raise forms.ValidationError("Votre commentaire doit contenir au moins 10 caractères.")

        allowed, msg = validate_content(commentaire)
        if not allowed:
            raise forms.ValidationError(msg)

        return commentaire



# ============================
# Review Filter Form
# ============================
class ReviewFilterForm(forms.Form):
    SORT_CHOICES = [
        ('-date_review', 'Plus récents'),
        ('date_review', 'Plus anciens'),
        ('-note', 'Meilleures notes'),
        ('note', 'Notes les plus basses'),
    ]

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rechercher...'})
    )
    min_note = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '5', 'step': '0.5'})
    )
    max_note = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '5', 'step': '0.5'})
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=SORT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
