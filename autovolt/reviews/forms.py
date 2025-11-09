from django import forms
from .models import Review, Commentaire


class ReviewForm(forms.ModelForm):
    """
    Form for creating and editing reviews
    """
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
                'placeholder': 'Décrivez votre expérience...',
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
            'description': 'Votre avis détaillé',
            'image': 'Image'
        }
        help_texts = {
            'note': 'Donnez une note entre 0 et 5 étoiles',
            'description': 'Partagez votre expérience en détail (minimum 50 caractères)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make image optional when editing an existing review
        if self.instance and self.instance.pk:
            self.fields['image'].required = False
    
    def clean_description(self):
        """Validate that description is at least 50 characters"""
        description = self.cleaned_data.get('description')
        if len(description) < 50:
            raise forms.ValidationError(
                'Votre avis doit contenir au moins 50 caractères.'
            )
        return description
    
    def clean_note(self):
        """Validate note is between 0 and 5"""
        note = self.cleaned_data.get('note')
        if note < 0 or note > 5:
            raise forms.ValidationError(
                'La note doit être entre 0 et 5.'
            )
        return note


class CommentaireForm(forms.ModelForm):
    """
    Form for creating and editing comments
    """
    class Meta:
        model = Commentaire
        fields = ['commentaire']
        widgets = {
            'commentaire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ajoutez votre commentaire...',
                'required': True
            })
        }
        labels = {
            'commentaire': 'Votre commentaire'
        }
    
    def clean_commentaire(self):
        """Validate that comment is at least 10 characters"""
        commentaire = self.cleaned_data.get('commentaire')
        if len(commentaire) < 10:
            raise forms.ValidationError(
                'Votre commentaire doit contenir au moins 10 caractères.'
            )
        return commentaire


class ReviewFilterForm(forms.Form):
    """
    Form for filtering reviews (User Story 8.6)
    """
    SORT_CHOICES = [
        ('-date_review', 'Plus récents'),
        ('date_review', 'Plus anciens'),
        ('-note', 'Meilleures notes'),
        ('note', 'Notes les plus basses'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher...'
        })
    )
    
    min_note = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '5',
            'step': '0.5',
            'placeholder': 'Note min'
        })
    )
    
    max_note = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '5',
            'step': '0.5',
            'placeholder': 'Note max'
        })
    )
    
    sort_by = forms.ChoiceField(
        required=False,
        choices=SORT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )