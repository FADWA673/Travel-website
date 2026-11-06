import logging
from django.db import connection

logger = logging.getLogger(__name__)

def debug_database_connection():
    """Vérifie et affiche des informations sur la connexion à la base de données"""
    try:
        # Vérifier si la connexion est active
        connection.ensure_connection()
        logger.info("Connexion à la base de données active")
        
        # Afficher des informations sur la connexion
        db_settings = connection.settings_dict
        logger.info(f"Base de données: {db_settings['NAME']}")
        logger.info(f"Utilisateur: {db_settings['USER']}")
        logger.info(f"Moteur: {db_settings['ENGINE']}")
        
        # Exécuter une requête simple pour tester la connexion
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            logger.info(f"Test de requête réussi: {result}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur de connexion à la base de données: {str(e)}")
        return False

def debug_train_reservations():
    """Affiche des informations sur les réservations de train dans la base de données"""
    from .models import TrainReservation
    
    try:
        # Compter le nombre total de réservations
        total = TrainReservation.objects.count()
        logger.info(f"Nombre total de réservations de train: {total}")
        
        # Afficher les 5 dernières réservations
        recent = TrainReservation.objects.all().order_by('-date_creation')[:5]
        logger.info("Réservations récentes:")
        for res in recent:
            logger.info(f"ID: {res.id}, Client: {res.client_id}, Départ: {res.depart}, Destination: {res.destination}, Date: {res.date_voyage}, Statut: {res.statut}")
        
        return total
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des réservations de train: {str(e)}")
        return 0
