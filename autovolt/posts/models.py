from django.db import models
from django.urls import reverse
from django.utils.html import format_html


class Post(models.Model):
    MARQUE_CHOICES = [
    # German
    ('Audi', 'Audi'),
    ('BMW', 'BMW'),
    ('Mercedes-Benz', 'Mercedes-Benz'),
    ('Volkswagen', 'Volkswagen'),
    ('Porsche', 'Porsche'),
    ('Opel', 'Opel'),
    ('Maybach', 'Maybach'),

    # Japanese
    ('Toyota', 'Toyota'),
    ('Honda', 'Honda'),
    ('Nissan', 'Nissan'),
    ('Mazda', 'Mazda'),
    ('Mitsubishi', 'Mitsubishi'),
    ('Subaru', 'Subaru'),
    ('Suzuki', 'Suzuki'),
    ('Lexus', 'Lexus'),
    ('Infiniti', 'Infiniti'),

    # American
    ('Ford', 'Ford'),
    ('Chevrolet', 'Chevrolet'),
    ('Dodge', 'Dodge'),
    ('Tesla', 'Tesla'),
    ('GMC', 'GMC'),
    ('Jeep', 'Jeep'),
    ('Cadillac', 'Cadillac'),
    ('Chrysler', 'Chrysler'),
    ('Lincoln', 'Lincoln'),
    ('Buick', 'Buick'),

    # British
    ('Land Rover', 'Land Rover'),
    ('Range Rover', 'Range Rover'),
    ('Jaguar', 'Jaguar'),
    ('Mini', 'Mini'),
    ('Bentley', 'Bentley'),
    ('Rolls-Royce', 'Rolls-Royce'),
    ('Aston Martin', 'Aston Martin'),
    ('Lotus', 'Lotus'),
    ('McLaren', 'McLaren'),

    # Italian
    ('Ferrari', 'Ferrari'),
    ('Lamborghini', 'Lamborghini'),
    ('Maserati', 'Maserati'),
    ('Alfa Romeo', 'Alfa Romeo'),
    ('Fiat', 'Fiat'),

    # French
    ('Peugeot', 'Peugeot'),
    ('Renault', 'Renault'),
    ('Citroën', 'Citroën'),
    ('DS Automobiles', 'DS Automobiles'),

    # Korean
    ('Hyundai', 'Hyundai'),
    ('Kia', 'Kia'),
    ('Genesis', 'Genesis'),

    # Swedish
    ('Volvo', 'Volvo'),
    ('Koenigsegg', 'Koenigsegg'),

    # Chinese
    ('BYD', 'BYD'),
    ('Geely', 'Geely'),
    ('NIO', 'NIO'),
    ('Great Wall', 'Great Wall'),
    ('Changan', 'Changan'),

    # Other / Miscellaneous
    ('Skoda', 'Skoda'),
    ('SEAT', 'SEAT'),
    ('Dacia', 'Dacia'),
    ('Tata', 'Tata'),
    ('Mahindra', 'Mahindra'),
    ('Proton', 'Proton'),
    ('Perodua', 'Perodua'),
    ('Smart', 'Smart'),
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
    CARROSSERIE_CHOICES = [
    ('Berline', 'Berline / Sedan'),
    ('Hatchback', 'Hatchback'),
    ('Break', 'Break / Station Wagon'),
    ('Coupé', 'Coupé'),
    ('Cabriolet', 'Cabriolet / Convertible'),
    ('SUV', 'SUV / 4x4 / Crossover'),
    ('Monospace', 'Monospace / Minivan'),
    ('Pick-up', 'Pick-up / Truck'),
    ('Utilitaire', 'Utilitaire / Van'),
    ('Sport', 'Sport'),
    ('Compacte', 'Compacte'),
    ('Roadster', 'Roadster'),
    ('Limousine', 'Limousine'),
    ('Autres', 'Autres'),
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
    carrosserie = models.CharField(
    max_length=50,
    choices=CARROSSERIE_CHOICES,
    default='Berline',
)

    nb_proprietes = models.IntegerField()
    gouvernerat = models.CharField(max_length=100)
    price = models.FloatField()
    image = models.ImageField(upload_to='posts/', default='default_car.jpg')
    dashboard_image = models.ImageField(upload_to='posts/', blank=True, null=True)
    owner = models.ForeignKey(
        'user_app.User',            
        on_delete=models.CASCADE,
        related_name='posts'
    )
    
    def __str__(self):
        return f"{self.marque} {self.modele} ({self.year})"
    
    def get_absolute_url(self):
        return reverse('post_detail', args=[self.pk])

    # Optionnel: aperçu image dans l’admin
    def image_preview(self):
        if self.image:
            return format_html('<img src="{}" style="height:80px;border-radius:6px;" />', self.image.url)
        return "-"
    image_preview.short_description = "Aperçu"

    class Meta:
        ordering = ['-id']