from django.db import models
from django.conf import settings
from vehicles.models import Voiture

class TestDrive(models.Model):
    STATUS_CHOICES = [
        ('cancelled', 'Cancelled'),
        ('done', 'Done'),
        ('not_done', 'Not done'),
    ]

    CITY_CHOICES = [
        ('Tunis', 'Tunis'),
        ('Ariana', 'Ariana'),
        ('La Marsa', 'La Marsa'),
        ('Carthage', 'Carthage'),
        ('Le Kram', 'Le Kram'),
        ('La Goulette', 'La Goulette'),
        ('Le Bardo', 'Le Bardo'),
        ('Ben Arous', 'Ben Arous'),
        ('Ezzahra', 'Ezzahra'),
        ('Rades', 'Rades'),
        ('Hammam-Lif', 'Hammam-Lif'),
        ('Hammam-Chatt', 'Hammam-Chatt'),
        ('Megrine', 'Megrine'),
        ('Mourouj', 'Mourouj'),
        ('Manouba', 'Manouba'),
        ('Oued Ellil', 'Oued Ellil'),
        ('Douar Hicher', 'Douar Hicher'),
    ]

    id_test_drive = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='test_drives'
    )
    car = models.ForeignKey(
        Voiture,
        on_delete=models.CASCADE,
        related_name='test_drives'
    )

    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    duration = models.PositiveIntegerField(default=30, help_text="Durée du test en minutes")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_done')

    test_location = models.CharField(
        max_length=255,
        choices=CITY_CHOICES,
        default='Tunis',
        help_text="Lieu du test drive"
    )

    comments = models.TextField(blank=True, null=True, help_text="Notes ou remarques du client")
    driver_license_number = models.CharField(max_length=20, blank=True, null=True, help_text="Numéro de permis du conducteur")
    contact_phone = models.CharField(max_length=15, blank=True, null=True, help_text="Numéro de téléphone du client")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    no_show_history = models.IntegerField(default=0, editable=False)
    reservation_count = models.IntegerField(default=0, editable=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        total_reservations = TestDrive.objects.filter(user=self.user).count()
        cancelled_reservations = TestDrive.objects.filter(user=self.user, status='cancelled').count()
        TestDrive.objects.filter(user=self.user).update(
            reservation_count=total_reservations,
            no_show_history=cancelled_reservations
        )

    def __str__(self):
        return f"TestDrive #{self.id_test_drive} - {{ t.user.first_name }} {{ t.user.last_name }} - {self.car.marque} {self.car.modele}"
