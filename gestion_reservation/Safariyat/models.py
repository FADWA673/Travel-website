from django.db import models
from django.contrib.auth.models import User

class ContactMessage(models.Model):
    """
    Model for storing contact form messages
    """
    nom_complet = models.CharField(max_length=100, verbose_name="Nom complet")
    email = models.EmailField(verbose_name="Email")
    sujet = models.CharField(max_length=200, verbose_name="Sujet")
    message = models.TextField(verbose_name="Message")
    date_envoi = models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")
    
    def __str__(self):
        return f"{self.nom_complet} - {self.sujet}"
    
    class Meta:
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
        ordering = ['-date_envoi']

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, default=None)  # Valeur par défaut
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Reservation(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    travel_date = models.DateTimeField()
    travel_type = models.CharField(max_length=50, choices=[('auto-bus', 'auto-Bus'), ('train', 'Train'), ('taxi', 'Taxi')])
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return "Reservation for {self.client.first_name} {self.client.last_name} from {self.origin} to {self.destination}"

class CompagnieTransport(models.Model):
    nom = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='logos_compagnies/', null=True, blank=True)
    description = models.TextField()
    site_web = models.URLField(blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    est_actif = models.BooleanField(default=True)

    def __str__(self):
        return self.nom


class Autobus(models.Model):
    compagnie = models.ForeignKey(CompagnieTransport, on_delete=models.CASCADE, related_name='autobus')
    numero_bus = models.CharField(max_length=20)
    type_bus = models.CharField(max_length=50, choices=[
        ('Standard', 'Standard'),
        ('Premium', 'Premium'),
        ('VIP', 'VIP'),
        ('Économique', 'Économique')
    ])
    capacite = models.PositiveIntegerField(default=50)
    est_climatise = models.BooleanField(default=True)
    wifi_disponible = models.BooleanField(default=False)
    prises_electriques = models.BooleanField(default=False)
    est_actif = models.BooleanField(default=True)
    
    
    def __str__(self):
        return f"{self.compagnie.nom} - {self.numero_bus}"
    
    class Meta:
        verbose_name = "Autobus"
        verbose_name_plural = "Autobus"

class TrajetAutobus(models.Model):
    autobus = models.ForeignKey(Autobus, on_delete=models.CASCADE, related_name='trajets')
    ville_depart = models.CharField(max_length=100)
    ville_arrivee = models.CharField(max_length=100)
    heure_depart = models.TimeField()
    heure_arrivee = models.TimeField()
    duree = models.CharField(max_length=20, blank=True)  # Calculé automatiquement
    jours_operation = models.CharField(max_length=20, help_text="Ex: Lun,Mar,Mer,Jeu,Ven,Sam,Dim")
    prix_standard = models.DecimalField(max_digits=10, decimal_places=2)
    places_disponibles = models.PositiveIntegerField(default=50)
    est_actif = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        # Calculer la durée automatiquement
        if self.heure_depart and self.heure_arrivee:
            # Convertir les heures en minutes
            dep_minutes = self.heure_depart.hour * 60 + self.heure_depart.minute
            arr_minutes = self.heure_arrivee.hour * 60 + self.heure_arrivee.minute
            
            # Gérer le cas où l'arrivée est le jour suivant
            if arr_minutes < dep_minutes:
                arr_minutes += 24 * 60
                
            # Calculer la différence en heures et minutes
            diff_minutes = arr_minutes - dep_minutes
            hours, minutes = divmod(diff_minutes, 60)
            
            self.duree = f"{hours}h{minutes:02d}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.ville_depart} - {self.ville_arrivee} ({self.heure_depart})"
    
    class Meta:
        verbose_name = "Trajet d'autobus"
        verbose_name_plural = "Trajets d'autobus"

class ClientFidelite(models.Model):
    """
    Modèle pour gérer la fidélité des clients
    """
    client = models.OneToOneField('Client', on_delete=models.CASCADE, related_name='fidelite')
    points = models.PositiveIntegerField(default=0, verbose_name="Points de fidélité")
    niveau = models.CharField(max_length=20, choices=[
        ('bronze', 'Bronze'),
        ('argent', 'Argent'),
        ('or', 'Or'),
        ('platine', 'Platine')
    ], default='bronze', verbose_name="Niveau de fidélité")
    date_inscription = models.DateField(auto_now_add=True, verbose_name="Date d'inscription")
    # Nous allons renommer ce champ pour éviter de créer une nouvelle migration
    date_mise_a_jour = models.DateTimeField(auto_now=True, verbose_name="Dernière mise à jour")
    
    def __str__(self):
        return f"Fidélité de {self.client} - {self.points} points ({self.niveau})"
    
    def obtenir_reduction(self):
        """
        Retourne le pourcentage de réduction en fonction du niveau
        """
        if self.niveau == 'bronze':
            return 5
        elif self.niveau == 'argent':
            return 10
        elif self.niveau == 'or':
            return 15
        else:  # platine
            return 20
    
    def ajouter_points(self, points):
        """
        Ajoute des points au client et met à jour son niveau
        """
        self.points += points
        
        # Mettre à jour le niveau en fonction des points
        if self.points >= 1000:
            self.niveau = 'platine'
        elif self.points >= 500:
            self.niveau = 'or'
        elif self.points >= 200:
            self.niveau = 'argent'
        else:
            self.niveau = 'bronze'
            
        self.save()
        return self.points
    
    class Meta:
        verbose_name = "Fidélité client"
        verbose_name_plural = "Fidélités clients"

# Ajout du modèle pour les annulations et modifications
class ModificationReservation(models.Model):
    TYPE_CHOICES = [
        ('annulation', 'Annulation'),
        ('modification', 'Modification')
    ]
    
    # Champs polymorphiques pour supporter différents types de réservations
    reservation_type = models.CharField(max_length=20, choices=[
        ('taxi', 'Taxi'),
        ('bus', 'Bus'),
        ('train', 'Train')
    ])
    reservation_id = models.IntegerField()
    
    type_modification = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date_demande = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=[
        ('en_attente', 'En attente'),
        ('approuvee', 'Approuvée'),
        ('refusee', 'Refusée')
    ], default='en_attente')
    
    # Détails de la modification
    raison = models.TextField()
    frais = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remboursement = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.get_type_modification_display()} - {self.get_reservation_type_display()} #{self.reservation_id}"

# Modification des modèles existants pour supporter les nouvelles fonctionnalités

# Ajouter des champs à TaxiReservation pour la politique d'annulation
class TaxiReservation(models.Model):
    # Champs existants...
    TYPE_CHOICES = [
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('familial', 'Familial'),
    ]

    depart = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    date = models.DateField()
    heure = models.TimeField()
    nombre_passagers = models.IntegerField()
    type_taxi = models.CharField(max_length=10, choices=TYPE_CHOICES)
    
    # Nouveaux champs pour les informations du taxi
    chauffeur_nom = models.CharField(max_length=100, blank=True, null=True)
    chauffeur_telephone = models.CharField(max_length=20, blank=True, null=True)
    numero_taxi = models.CharField(max_length=20, blank=True, null=True)
    statut = models.CharField(max_length=20, default='en_attente', choices=[
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
        ('modifiee', 'Modifiée')  # Nouveau statut
    ])
    notes_admin = models.TextField(blank=True, null=True)
    ticket_envoye = models.BooleanField(default=False, verbose_name="Ticket envoyé")
    
    # Nouveaux champs pour la politique d'annulation
    politique_annulation = models.CharField(max_length=20, choices=[
        ('flexible', 'Flexible (100% jusqu\'à 24h avant)'),
        ('moderee', 'Modérée (50% jusqu\'à 24h avant)'),
        ('stricte', 'Stricte (Non remboursable)')
    ], default='moderee')
    
    # Champ pour stocker l'email du passager
    email_passager = models.EmailField(blank=True, null=True)
    telephone_passager = models.CharField(max_length=20, blank=True, null=True)
    
    # Champ pour lier à un client (pour le système de fidélité)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations_taxi')
    
    # Prix total pour faciliter les comparaisons
    prix_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.depart} → {self.destination} ({self.date} à {self.heure})"
    
    def peut_annuler(self):
        """Vérifie si la réservation peut être annulée selon la politique"""
        from datetime import datetime, timedelta
        
        # Si la réservation est déjà annulée ou terminée
        if self.statut in ['annulee', 'terminee']:
            return False, 0, "La réservation ne peut plus être annulée."
        
        # Calculer la différence entre maintenant et la date/heure de réservation
        now = datetime.now()
        reservation_datetime = datetime.combine(self.date, self.heure)
        
        # Si la réservation est dans le passé
        if now > reservation_datetime:
            return False, 0, "La réservation est déjà passée."
        
        # Calculer le délai en heures
        delai = (reservation_datetime - now).total_seconds() / 3600
        
        # Appliquer la politique d'annulation
        if self.politique_annulation == 'flexible':
            if delai >= 24:
                return True, 100, "Remboursement à 100%"
            elif delai >= 12:
                return True, 50, "Remboursement à 50%"
            else:
                return True, 0, "Aucun remboursement"
        elif self.politique_annulation == 'moderee':
            if delai >= 24:
                return True, 50, "Remboursement à 50%"
            else:
                return True, 0, "Aucun remboursement"
        else:  # stricte
            return True, 0, "Aucun remboursement selon la politique stricte"

# Ajouter des champs similaires à AutobusReservation
class AutobusReservation(models.Model):
    # Champs existants...
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='reservations_autobus', null=True, blank=True)
    trajet = models.ForeignKey(TrajetAutobus, on_delete=models.CASCADE, related_name='reservations')
    date_voyage = models.DateField()
    nombre_passagers = models.PositiveIntegerField(default=1)
    prix_total = models.DecimalField(max_digits=10, decimal_places=2)
    nom_passager = models.CharField(max_length=100)
    email_passager = models.EmailField()
    telephone_passager = models.CharField(max_length=20)
    statut = models.CharField(max_length=20, choices=[
        ('en_attente', 'En attente'),
        ('confirmee', 'Confirmée'),
        ('annulee', 'Annulée'),
        ('terminee', 'Terminée'),
        ('modifiee', 'Modifiée')  # Nouveau statut
    ], default='en_attente')
    methode_paiement = models.CharField(max_length=20, choices=[
        ('card', 'Carte bancaire'),
        ('counter', 'Au comptoir')
    ], default='card')
    date_creation = models.DateTimeField(auto_now_add=True)
    ticket_envoye = models.BooleanField(default=False, verbose_name="Ticket envoyé")
    
    # Nouveaux champs pour la politique d'annulation
    politique_annulation = models.CharField(max_length=20, choices=[
        ('flexible', 'Flexible (100% jusqu\'à 24h avant)'),
        ('moderee', 'Modérée (50% jusqu\'à 24h avant)'),
        ('stricte', 'Stricte (Non remboursable)')
    ], default='moderee')
    
    def __str__(self):
        return f"Réservation {self.id} - {self.trajet.ville_depart} → {self.trajet.ville_arrivee}"
    
    class Meta:
        verbose_name = "Réservation d'autobus"
        verbose_name_plural = "Réservations d'autobus"
    
    def peut_annuler(self):
        """Vérifie si la réservation peut être annulée selon la politique"""
        from datetime import datetime, timedelta
        
        # Si la réservation est déjà annulée ou terminée
        if self.statut in ['annulee', 'terminee']:
            return False, 0, "La réservation ne peut plus être annulée."
        
        # Calculer la différence entre maintenant et la date de voyage
        now = datetime.now().date()
        
        # Si la réservation est dans le passé
        if now > self.date_voyage:
            return False, 0, "La réservation est déjà passée."
        
        # Calculer le délai en jours
        delai = (self.date_voyage - now).days
        
        # Appliquer la politique d'annulation
        if self.politique_annulation == 'flexible':
            if delai >= 1:
                return True, 100, "Remboursement à 100%"
            else:
                return True, 0, "Aucun remboursement"
        elif self.politique_annulation == 'moderee':
            if delai >= 1:
                return True, 50, "Remboursement à 50%"
            else:
                return True, 0, "Aucun remboursement"
        else:  # stricte
            return True, 0, "Aucun remboursement selon la politique stricte"


# Modèle pour l'intégration avec les services de transport locaux
class ServiceTransportLocal(models.Model):
    nom = models.CharField(max_length=100)
    type_service = models.CharField(max_length=20, choices=[
        ('taxi', 'Taxi'),
        ('bus', 'Bus'),
        ('train', 'Train'),
        ('vtc', 'VTC'),
        ('autre', 'Autre')
    ])
    ville = models.CharField(max_length=100)
    adresse = models.TextField(blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    site_web = models.URLField(blank=True, null=True)
    
    # Nouveaux champs pour les caractéristiques
    wifi_disponible = models.BooleanField(default=False, verbose_name="WiFi disponible")
    climatisation = models.BooleanField(default=False, verbose_name="Climatisation")
    prises_electriques = models.BooleanField(default=False, verbose_name="Prises électriques")
    accessibilite_pmr = models.BooleanField(default=False, verbose_name="Accessibilité PMR")
    
    # Nouveaux champs pour les horaires
    horaires_ouverture = models.CharField(max_length=100, blank=True, null=True, verbose_name="Horaires d'ouverture", 
                                         help_text="Ex: 08:00-20:00")
    jours_service = models.CharField(max_length=100, blank=True, null=True, verbose_name="Jours de service",
                                    help_text="Ex: Lun-Dim ou Lun,Mar,Mer,Jeu,Ven")
    
    # Informations d'API pour l'intégration
    api_url = models.URLField(blank=True, null=True)
    api_key = models.CharField(max_length=100, blank=True, null=True)
    api_secret = models.CharField(max_length=100, blank=True, null=True)
    
    # Statut de l'intégration
    est_actif = models.BooleanField(default=True)
    date_integration = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nom} ({self.get_type_service_display()} - {self.ville})"
    
    class Meta:
        verbose_name = "Service de transport local"
        verbose_name_plural = "Services de transport locaux"

class Prix(models.Model):
    """
    Modèle pour gérer les prix des différents services de transport
    """
    TYPE_SERVICE_CHOICES = [
        ('service_depart', 'Service de départ'),
        ('service_principal', 'Service principal'),
        ('service_arrivee', 'Service d\'arrivée'),
        ('taxi_standard', 'Taxi Standard'),
        ('taxi_premium', 'Taxi Premium'),
        ('taxi_familial', 'Taxi Familial'),
        ('bus_standard', 'Bus Standard'),
        ('bus_premium', 'Bus Premium'),
        ('bus_vip', 'Bus VIP'),
        ('train_standard', 'Train Standard'),
        ('train_premiere', 'Train Première Classe'),
    ]
    
    nom = models.CharField(max_length=100, help_text="Nom du service")
    type_service = models.CharField(max_length=50, choices=TYPE_SERVICE_CHOICES, help_text="Type de service")
    prix_base = models.DecimalField(max_digits=10, decimal_places=2, help_text="Prix de base en DH")
    prix_par_km = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Prix par km (pour les taxis)")
    prix_par_passager_supp = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Supplément par passager au-delà de 2")
    description = models.TextField(blank=True, null=True, help_text="Description du service et de sa tarification")
    est_actif = models.BooleanField(default=True, help_text="Indique si ce tarif est actif")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Prix"
        verbose_name_plural = "Prix"
        ordering = ['type_service', 'nom']
    
    def __str__(self):
        return f"{self.nom} ({self.prix_base} DH)"
    
    def calculer_prix(self, distance=0, nombre_passagers=1):
        """
        Calcule le prix final en fonction de la distance et du nombre de passagers
        """
        prix = self.prix_base
        
        # Ajouter le prix par km si applicable
        if self.prix_par_km > 0 and distance > 0:
            prix += self.prix_par_km * distance
        
        # Ajouter le supplément par passager si applicable
        if self.prix_par_passager_supp > 0 and nombre_passagers > 2:
            prix += self.prix_par_passager_supp * (nombre_passagers - 2)
        
        return prix

class TrainStation(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom de la gare")
    city = models.CharField(max_length=100, verbose_name="Ville")
    code = models.CharField(max_length=10, blank=True, null=True, verbose_name="Code")
    
    class Meta:
        verbose_name = "Gare"
        verbose_name_plural = "Gares"
        ordering = ['city', 'name']
    
    def __str__(self):
        return f"{self.city} - {self.name}"

class TrainRoute(models.Model):
    departure_station = models.ForeignKey(TrainStation, on_delete=models.CASCADE, related_name='departure_routes', verbose_name="Gare de départ")
    arrival_station = models.ForeignKey(TrainStation, on_delete=models.CASCADE, related_name='arrival_routes', verbose_name="Gare d'arrivée")
    distance = models.IntegerField(blank=True, null=True, verbose_name="Distance (km)")
    
    class Meta:
        verbose_name = "Trajet"
        verbose_name_plural = "Trajets"
        ordering = ['departure_station__city', 'arrival_station__city']
        unique_together = ['departure_station', 'arrival_station']
    
    def __str__(self):
        return f"{self.departure_station.city} → {self.arrival_station.city}"

class TrainType(models.Model):
    name = models.CharField(max_length=50, verbose_name="Nom du train")
    code = models.CharField(max_length=20, verbose_name="Code")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    
    class Meta:
        verbose_name = "Type de train"
        verbose_name_plural = "Types de train"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class TrainSchedule(models.Model):
    route = models.ForeignKey(TrainRoute, on_delete=models.CASCADE, related_name='schedules', verbose_name="Trajet")
    train_type = models.ForeignKey(TrainType, on_delete=models.CASCADE, verbose_name="Type de train")
    departure_time = models.TimeField(verbose_name="Heure de départ")
    arrival_time = models.TimeField(verbose_name="Heure d'arrivée")
    duration = models.DurationField(blank=True, null=True, verbose_name="Durée")
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Prix (MAD)")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    days_of_week = models.CharField(max_length=7, default="1111111", help_text="Jours de la semaine (1=actif, 0=inactif, ordre: lundi à dimanche)", verbose_name="Jours de service")
    
    class Meta:
        verbose_name = "Horaire de train"
        verbose_name_plural = "Horaires de train"
        ordering = ['route', 'departure_time']
    
    def __str__(self):
        return f"{self.route} - {self.departure_time.strftime('%H:%M')}"
    
    def save(self, *args, **kwargs):
        # Calculer automatiquement la durée si elle n'est pas définie
        if not self.duration and self.departure_time and self.arrival_time:
            from datetime import datetime, timedelta
            
            # Convertir les heures en objets datetime pour calculer la différence
            dt1 = datetime.combine(datetime.today(), self.departure_time)
            dt2 = datetime.combine(datetime.today(), self.arrival_time)
            
            # Si l'arrivée est avant le départ, ajouter un jour
            if dt2 < dt1:
                dt2 = dt2 + timedelta(days=1)
            
            self.duration = dt2 - dt1
        
        super().save(*args, **kwargs)
    
    def get_duration_display(self):
        """Retourne la durée au format heures et minutes."""
        if not self.duration:
            return "N/A"
        
        total_seconds = self.duration.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        
        if minutes:
            return f"{hours}h{minutes:02d}"
        return f"{hours}h"
    
    def is_available_on_date(self, date):
        """Vérifie si le train circule à cette date."""
        # Obtenir le jour de la semaine (0=lundi, 6=dimanche)
        weekday = date.weekday()
        # Vérifier si le train circule ce jour-là
        return self.days_of_week[weekday] == '1'

# Ajoutez cette fonction à votre fichier models.py
# Assurez-vous d'importer les modèles nécessaires

def get_or_create_client(user):
    """
    Récupère le profil client d'un utilisateur ou en crée un s'il n'existe pas
    """
    from django.contrib.auth.models import User
    
    try:
        # Essayer de récupérer le client
        return Client.objects.get(user=user)
    except Client.DoesNotExist:
        # Créer un nouveau client si aucun n'existe
        client = Client.objects.create(
            user=user,
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            email=user.email or "",
            phone_number=""
        )
        
        # Créer un profil de fidélité
        ClientFidelite.objects.create(
            client=client,
            points=0,
            niveau='bronze'
        )
        
        return client

# Assurez-vous que le modèle TrainReservation est correctement défini
class TrainReservation(models.Model):
    """
    Modèle pour les réservations de train
    """
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='train_reservations')
    depart = models.CharField(max_length=100, verbose_name="Gare de départ")
    destination = models.CharField(max_length=100, verbose_name="Gare d'arrivée")
    date_voyage = models.DateField(verbose_name="Date du voyage")
    nb_passagers = models.PositiveIntegerField(default=1, verbose_name="Nombre de passagers")
    classe = models.CharField(max_length=20, choices=[
        ('premiere', 'Première classe'),
        ('seconde', 'Seconde classe')
    ], default='seconde', verbose_name="Classe")
    prix = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prix total")
    statut = models.CharField(max_length=20, choices=[
        ('en_attente', 'En attente'),
        ('confirmé', 'Confirmé'),
        ('annulée', 'Annulée'),
        ('modifiée', 'Modifiée')
    ], default='en_attente', verbose_name="Statut")
    numero_siege = models.CharField(max_length=10, blank=True, null=True, verbose_name="Numéro de siège")
    train_schedule = models.ForeignKey('TrainSchedule', on_delete=models.SET_NULL, null=True, blank=True, related_name='reservations')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    ticket_envoye = models.BooleanField(default=False, verbose_name="Ticket envoyé")
    
    def __str__(self):
        return f"Réservation train {self.id} - {self.depart} → {self.destination} ({self.date_voyage})"
    
    def peut_annuler(self):
        """
        Vérifie si la réservation peut être annulée et calcule le pourcentage de remboursement
        Retourne un tuple (peut_annuler, pourcentage_remboursement, message)
        """
        import datetime
        
        if self.statut == 'annulée':
            return (False, 0, "La réservation est déjà annulée.")
        
        # Calculer le nombre de jours avant le départ
        aujourd_hui = datetime.date.today()
        jours_avant_depart = (self.date_voyage - aujourd_hui).days
        
        if jours_avant_depart < 0:
            return (False, 0, "Le voyage a déjà eu lieu.")
        elif jours_avant_depart == 0:
            return (False, 0, "Impossible d'annuler le jour même du départ.")
        elif jours_avant_depart <= 1:
            return (True, 50, "Annulation possible avec 50% de remboursement (J-1).")
        elif jours_avant_depart <= 3:
            return (True, 75, "Annulation possible avec 75% de remboursement (J-3).")
        else:
            return (True, 100, "Annulation possible avec remboursement complet.")
    
    class Meta:
        verbose_name = "Réservation de train"
        verbose_name_plural = "Réservations de train"
        ordering = ['-date_voyage']

# Ajoutez ce modèle à votre fichier models.py s'il n'existe pas déjà

# Ajoutez ce modèle à votre fichier models.py s'il n'existe pas déjà

class PorteAPorteReservation(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE, null=True, blank=True)
    adresse_depart = models.CharField(max_length=255, verbose_name="Adresse de départ")
    adresse_destination = models.CharField(max_length=255, verbose_name="Adresse de destination")
    date = models.DateTimeField(verbose_name="Date et heure du voyage")
    nb_passagers = models.PositiveIntegerField(default=1, verbose_name="Nombre de passagers")
    bagages = models.PositiveIntegerField(default=0, verbose_name="Nombre de bagages")
    commentaire = models.TextField(blank=True, null=True, verbose_name="Commentaires")
    
    # Services sélectionnés (références aux IDs des services)
    service_depart_id = models.IntegerField(null=True, blank=True, verbose_name="Service de départ")
    service_principal_id = models.IntegerField(null=True, blank=True, verbose_name="Service principal")
    service_arrivee_id = models.IntegerField(null=True, blank=True, verbose_name="Service d'arrivée")
    
    # Options de transport
    option_taxi = models.BooleanField(default=True, verbose_name="Option taxi")
    option_bus = models.BooleanField(default=True, verbose_name="Option bus")
    option_train = models.BooleanField(default=True, verbose_name="Option train")
    
    # Informations de paiement et statut
    prix = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Prix total")
    statut = models.CharField(max_length=20, choices=[
        ('en_attente', 'En attente'),
        ('confirmé', 'Confirmé'),
        ('annulé', 'Annulé'),
        ('terminé', 'Terminé')
    ], default='en_attente', verbose_name="Statut")
    
    # Champs de suivi
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Dernière modification")
    
    def __str__(self):
        return f"Porte à Porte: {self.adresse_depart} - {self.adresse_destination} ({self.date})"
    
    class Meta:
        verbose_name = "Réservation porte-à-porte"
        verbose_name_plural = "Réservations porte-à-porte"
        ordering = ['-date_creation']
    
    def get_service_depart(self):
        """Récupère l'objet service de départ"""
        if self.service_depart_id:
            from .models import ServiceTransportLocal
            try:
                return ServiceTransportLocal.objects.get(id=self.service_depart_id)
            except ServiceTransportLocal.DoesNotExist:
                return None
        return None
    
    def get_service_principal(self):
        """Récupère l'objet service principal"""
        if self.service_principal_id:
            from .models import ServiceTransportLocal
            try:
                return ServiceTransportLocal.objects.get(id=self.service_principal_id)
            except ServiceTransportLocal.DoesNotExist:
                return None
        return None
    
    def get_service_arrivee(self):
        """Récupère l'objet service d'arrivée"""
        if self.service_arrivee_id:
            from .models import ServiceTransportLocal
            try:
                return ServiceTransportLocal.objects.get(id=self.service_arrivee_id)
            except ServiceTransportLocal.DoesNotExist:
                return None
        return None
