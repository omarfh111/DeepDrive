from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import time
from .models import TestDrive
from vehicles.models import Voiture
import re

class TestDriveForm(forms.ModelForm):
    class Meta:
        model = TestDrive
        fields = [
            'car', 'reservation_date', 'reservation_time', 'duration',
            'test_location', 'comments', 'driver_license_number', 'contact_phone'
        ]
        labels = {
            'car': "Select a car:",
            'reservation_date': "Reservation date:",
            'reservation_time': "Reservation time:",
            'duration': "Test duration (minutes):",
            'test_location': "Test location:",
            'comments': "Comments:",
            'driver_license_number': "Driver license number:",
            'contact_phone': "Contact phone:",
        }
        widgets = {
            'car': forms.Select(attrs={'class': 'form-select'}),
            'reservation_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reservation_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'min': '10', 'max': '60', 'step': '5'}),
            'test_location': forms.Select(attrs={'class': 'form-select'}),
            'comments': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'driver_license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '8 chiffres, ex: 28276314'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['car'].queryset = Voiture.objects.all()
        self.fields['car'].label_from_instance = lambda obj: f"{obj.marque} {obj.modele}"
        for field in self.fields.values():
            field.required = True

        # Si instance existe, pré-remplir contact_phone sans +216
        if self.instance and self.instance.contact_phone:
            phone = self.instance.contact_phone
            if phone.startswith("+216"):
                self.initial['contact_phone'] = phone[4:]

    def clean_reservation_date(self):
        date = self.cleaned_data.get('reservation_date')
        today = timezone.now().date()
        if date <= today:
            raise ValidationError("The reservation date must be in the future.")
        return date

    def clean_reservation_time(self):
        res_time = self.cleaned_data.get('reservation_time')
        if res_time < time(8, 0) or res_time > time(17, 0):
            raise ValidationError("The reservation time must be between 08:00 and 17:00.")
        return res_time

    def clean_duration(self):
        duration = self.cleaned_data.get('duration')
        if duration > 60:
            raise ValidationError("The test drive duration cannot exceed 60 minutes.")
        return duration

    def clean_comments(self):
        comments = self.cleaned_data.get('comments', '')
        if len(comments) > 100:
            raise ValidationError("Comments cannot exceed 100 characters.")
        return comments

    def clean_contact_phone(self):
        phone = self.cleaned_data.get('contact_phone', '').strip()
        # Supprimer tout sauf chiffres
        digits = re.sub(r'\D', '', phone)
        if len(digits) != 8:
            raise ValidationError("The phone number must contain exactly 8 digits.")
        # Retourner au format international pour Twilio
        return f"+216{digits}"


class TestDriveUpdateForm(TestDriveForm):
    class Meta(TestDriveForm.Meta):
        fields = TestDriveForm.Meta.fields + ['status']
        widgets = {**TestDriveForm.Meta.widgets, 'status': forms.Select(attrs={'class': 'form-select'})}
        labels = {**TestDriveForm.Meta.labels, 'status': "Status:"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bloquer le champ status si le test drive est déjà fait ou annulé
        if self.instance and self.instance.status in ['done', 'cancelled']:
            self.fields['status'].disabled = True