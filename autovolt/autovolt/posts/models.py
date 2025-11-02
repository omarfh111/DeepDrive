from django.db import models

class Post(models.Model):
    MARQUE_CHOICES = [
        ('Mercedes-Benz', 'Mercedes-Benz'),
        ('BMW', 'BMW'),
        ('Audi', 'Audi'),
        ('Volkswagen', 'Volkswagen'),
        ('Toyota', 'Toyota'),
        ('Other', 'Other'),
    ]

    ENERGY_CHOICES = [
        ('Essence', 'Essence'),
        ('Diesel', 'Diesel'),
        ('Electrique', 'Electrique'),
        ('Hybride', 'Hybride'),
    ]

    TRANSMISSION_CHOICES = [
        ('Traction', 'Traction'),
        ('Propulsion', 'Propulsion'),
        ('Integrale', 'Integrale'),
    ]

    ETAT_CHOICES = [
        ('Excellent', 'Excellent'),
        ('Bon', 'Bon'),
        ('Moyen', 'Moyen'),
        ('Mauvais', 'Mauvais'),
    ]

    marque = models.CharField(max_length=100, choices=MARQUE_CHOICES)
    modele = models.CharField(max_length=100)
    year = models.IntegerField()
    kilometrage = models.FloatField()
    energy = models.CharField(max_length=20, choices=ENERGY_CHOICES)
    boite_vitesse = models.CharField(max_length=20, choices=[('Manuelle', 'Manuelle'), ('Automatique', 'Automatique')])
    puissance_fiscale = models.IntegerField()
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    etat_general = models.CharField(max_length=20, choices=ETAT_CHOICES)
    carrosserie = models.CharField(max_length=50)
    nb_proprietes = models.IntegerField()
    gouvernerat = models.CharField(max_length=100)
    price = models.FloatField()
    image = models.ImageField(upload_to='posts/', default='default_car.jpg')

    def __str__(self):
        return f"{self.marque} {self.modele} ({self.year})"
