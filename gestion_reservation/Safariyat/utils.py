from urllib.parse import urlencode
import random
import datetime
import logging

logger = logging.getLogger(__name__)


def calculer_prix_taxi(depart, destination, nombre_passagers):
    """
    Calcule le prix estimé d'un trajet en taxi entre deux villes
    
    Args:
        depart: Ville de départ
        destination: Ville de destination
        nombre_passagers: Nombre de passagers
        
    Returns:
        float: Prix estimé en DH
    """
    # Distances approximatives entre les grandes villes marocaines (en km)
    distances = {
        ('casablanca', 'rabat'): 87,
        ('casablanca', 'marrakech'): 242,
        ('casablanca', 'fes'): 290,
        ('casablanca', 'tanger'): 338,
        ('casablanca', 'agadir'): 460,
        ('rabat', 'marrakech'): 324,
        ('rabat', 'fes'): 207,
        ('rabat', 'tanger'): 250,
        ('rabat', 'agadir'): 547,
        ('marrakech', 'fes'): 530,
        ('marrakech', 'tanger'): 650,
        ('marrakech', 'agadir'): 256,
        ('fes', 'tanger'): 399,
        ('fes', 'agadir'): 750,
        ('tanger', 'agadir'): 800
    }
    
    # Normaliser les noms de villes
    depart_norm = depart.lower().strip()
    destination_norm = destination.lower().strip()
    
    # Chercher la distance
    distance = None
    for (ville1, ville2), dist in distances.items():
        if (depart_norm in ville1 or ville1 in depart_norm) and (destination_norm in ville2 or ville2 in destination_norm):
            distance = dist
            break
        elif (depart_norm in ville2 or ville2 in depart_norm) and (destination_norm in ville1 or ville1 in destination_norm):
            distance = dist
            break
    
    # Si la distance n'est pas trouvée, estimer à partir des coordonnées (exemple simplifié)
    if distance is None:
        # Coordonnées approximatives des villes (latitude, longitude)
        coordonnees = {
            'casablanca': (33.5731, -7.5898),
            'rabat': (34.0209, -6.8416),
            'marrakech': (31.6295, -7.9811),
            'fes': (34.0181, -5.0078),
            'tanger': (35.7595, -5.8340),
            'agadir': (30.4278, -9.5981)
        }
        
        # Trouver les coordonnées les plus proches pour chaque ville
        depart_coords = None
        dest_coords = None
        
        for ville, coords in coordonnees.items():
            if ville in depart_norm or depart_norm in ville:
                depart_coords = coords
            if ville in destination_norm or destination_norm in ville:
                dest_coords = coords
        
        # Calculer la distance euclidienne (très approximatif)
        if depart_coords and dest_coords:
            import math
            lat1, lon1 = depart_coords
            lat2, lon2 = dest_coords
            
            # Formule de la distance euclidienne (à vol d'oiseau)
            distance = math.sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2) * 111  # 1 degré ≈ 111 km
        else:
            # Distance par défaut si aucune information n'est disponible
            distance = 200
    
    # Calculer le prix de base (2 DH/km pour les premiers 100 km, 1.5 DH/km au-delà)
    if distance <= 100:
        prix_base = distance * 2
    else:
        prix_base = 100 * 2 + (distance - 100) * 1.5
    
    # Ajuster en fonction du nombre de passagers
    if int(nombre_passagers) <= 4:
        # Prix standard pour 1-4 passagers
        prix_final = prix_base
    else:
        # Supplément pour plus de 4 passagers (taxi plus grand)
        prix_final = prix_base * 1.5
    
    # Arrondir à l'entier supérieur
    return round(prix_final)

def ajouter_points_fidelite(client, montant):
    """
    Ajoute des points de fidélité à un client en fonction du montant dépensé
    
    Args:
        client: Objet Client
        montant: Montant dépensé en DH
        
    Returns:
        int: Nombre de points ajoutés
    """
    from .models import ClientFidelite
    
    # Règle: 1 point pour chaque tranche de 10 DH dépensés
    points_a_ajouter = int(montant / 10)
    
    # Récupérer ou créer le profil de fidélité
    fidelite, created = ClientFidelite.objects.get_or_create(
        client=client,
        defaults={'points': 0, 'niveau': 'bronze'}
    )
    
    # Ajouter les points
    fidelite.points += points_a_ajouter
    
    # Mettre à jour le niveau
    fidelite.calculer_niveau()
    
    # Sauvegarder
    fidelite.save()
    
    return points_a_ajouter

def verifier_disponibilite_service_local(service_id, date, heure):
    """
    Vérifie la disponibilité d'un service de transport local
    
    Args:
        service_id: ID du service
        date: Date du service
        heure: Heure du service
        
    Returns:
        bool: True si disponible, False sinon
    """
    from .models import ServiceTransportLocal
    
    try:
        service = ServiceTransportLocal.objects.get(id=service_id)
        
        # Pour l'exemple, on considère que tous les services sont disponibles
        # Dans une implémentation réelle, il faudrait interroger l'API du service
        
        # Simuler une disponibilité aléatoire pour les tests
        return random.choice([True, True, True, False])  # 75% de chances d'être disponible
        
    except ServiceTransportLocal.DoesNotExist:
        return False

def calculer_prix_service(type_service, distance=0, nombre_passagers=1):
    """
    Calcule le prix d'un service en fonction de son type, de la distance et du nombre de passagers
    
    Args:
        type_service: Type de service (service_depart, service_principal, etc.)
        distance: Distance en km (pour les taxis)
        nombre_passagers: Nombre de passagers
        
    Returns:
        float: Prix calculé
    """
    try:
        # Récupérer le prix depuis la base de données
        from .models import Prix
        prix = Prix.objects.get(type_service=type_service, est_actif=True)
        
        # Calculer le prix final
        return prix.calculer_prix(distance, nombre_passagers)
    except Exception as e:
        logger.error(f"Erreur lors du calcul du prix pour {type_service}: {str(e)}")
        # Valeurs par défaut si le prix n'est pas défini dans la base de données
        default_prices = {
            'service_depart': 50,
            'service_principal': 100,
            'service_arrivee': 50,
            'taxi_standard': 150,
            'taxi_premium': 250,
            'taxi_familial': 350,
            'bus_standard': 80,
            'bus_premium': 120,
            'bus_vip': 200,
            'train_standard': 100,
            'train_premiere': 200
        }
        
        return default_prices.get(type_service, 0)


from .models import TrainRoute, TrainSchedule
import datetime

def comparer_prix(depart, destination, date_voyage, comparaison):
    """
    Compare train prices from the database.
    """
    try:
        routes = TrainRoute.objects.filter(
            departure_station__city__icontains=depart,
            arrival_station__city__icontains=destination
        )
        if routes.exists():
            schedules = TrainSchedule.objects.filter(route__in=routes, is_active=True)
            if schedules.exists():
                # Get the lowest price
                prix_train = min(schedule.price for schedule in schedules)
                comparaison.prix_train = prix_train
    except Exception as e:
        print(f"Error getting train prices: {e}")
        pass

from django.contrib.auth.models import User
from .models import Client

def get_or_create_client(user):
    """
    Récupère ou crée un client associé à un utilisateur.
    
    Args:
        user (User): L'utilisateur Django
        
    Returns:
        Client: L'instance du client associé à l'utilisateur
    """
    if not user or not user.is_authenticated:
        return None
        
    try:
        # Essayer de récupérer le client existant
        client = Client.objects.get(user=user)
        return client
    except Client.DoesNotExist:
        # Créer un nouveau client si aucun n'existe
        client = Client.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email
        )
        return client

def format_price(price):
    """
    Formate un prix en ajoutant le symbole de la devise.
    
    Args:
        price (float): Le prix à formater
        
    Returns:
        str: Le prix formaté
    """
    return f"{price:.2f} DH"


logger = logging.getLogger(__name__)

def calculate_train_price(base_price, classe, nb_passagers):
    """
    Calcule le prix total d'une réservation de train.

    Args:
        base_price (float): Le prix de base
        classe (str): La classe ('premiere' ou 'seconde')
        nb_passagers (int): Le nombre de passagers
        
    Returns:
        float: Le prix total
    """
    # Appliquer un multiplicateur selon la classe
    multiplicateur = 1.5 if classe == 'premiere' else 1.0

    # Calculer le prix total
    prix_total = base_price * multiplicateur * int(nb_passagers)

    return prix_total
# Ajoutez cette fonction à votre fichier utils.py
def mettre_a_jour_points_fidelite(client, montant):
    """
    Met à jour les points de fidélité d'un client en fonction du montant dépensé
    1 DH = 1 point de fidélité
    
    Retourne le nombre de points ajoutés
    """
    from .models import ClientFidelite
    
    # Convertir le montant en points (1 DH = 1 point)
    points_a_ajouter = int(montant)
    
    # Récupérer ou créer le profil de fidélité du client
    fidelite, created = ClientFidelite.objects.get_or_create(
        client=client,
        defaults={'points': 0, 'niveau': 'bronze'}
    )
    
    # Ajouter les points
    fidelite.points += points_a_ajouter
    
    # Mettre à jour le niveau en fonction des points
    if fidelite.points >= 1000:
        fidelite.niveau = 'platine'
    elif fidelite.points >= 500:
        fidelite.niveau = 'or'
    elif fidelite.points >= 200:
        fidelite.niveau = 'argent'
    else:
        fidelite.niveau = 'bronze'
    
    # Sauvegarder les modifications
    fidelite.save()
    
    return points_a_ajouter
