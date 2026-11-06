from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.contrib import messages
from django.http import HttpResponse, JsonResponse

# Import models directly
from .models import (
    Reservation, TrajetAutobus, Client, ClientFidelite, TaxiReservation, 
    AutobusReservation, TrainReservation, CompagnieTransport,
    ModificationReservation, ServiceTransportLocal, PorteAPorteReservation,
    TrainSchedule, TrainRoute, TrainStation, ContactMessage
)

# Then import forms
from .forms import ReservationForm, TaxiReservationForm, AnnulationForm, ModificationForm, PorteAPorteForm, TrainSearchForm, ContactForm

from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.db.models import Q
from .utils import calculer_prix_service, calculer_prix_taxi, get_or_create_client, calculate_train_price
from .pdf_utils import send_ticket_email, generate_pdf_ticket

import datetime
import uuid
import logging
import traceback
from threading import Thread


# Configurer le logger
logger = logging.getLogger(__name__)

def accueil(request):
    if request.method == 'POST':
        depart = request.POST.get('depart')
        destination = request.POST.get('destination')
        date_voyage = request.POST.get('date_voyage')
        nombre_passagers = int(request.POST.get('nombre_passagers'))

        # Validation simple (à améliorer)
        if not all([depart, destination, date_voyage, nombre_passagers]):
            return render(request, 'Safariyat/accueil.html', {'error': 'Veuillez remplir tous les champs.'})

        # Ici, vous pouvez appeler vos fonctions de recherche et de comparaison
        # Pour l'instant, on va juste créer un objet de comparaison vide
        class ComparaisonResultat:
            def __init__(self):
                self.prix_avion = None
                self.prix_bus = None
                self.prix_train = None

        comparaison = ComparaisonResultat()

        # Exemple de prix (à remplacer par vos vrais résultats)
        comparaison.prix_avion = calculer_prix_service('avion_standard', 100, nombre_passagers)

        # 2. Prix du bus - Utiliser la base de données au lieu du scraper
        from django.db.models import Min
        trajets_bus = TrajetAutobus.objects.filter(
            ville_depart__iexact=depart,
            ville_arrivee__iexact=destination,
            est_actif=True,
            places_disponibles__gte=nombre_passagers
        )
        
        if trajets_bus.exists():
            # Prendre le prix le plus bas parmi les trajets disponibles
            prix_min = trajets_bus.aggregate(Min('prix_standard'))['prix_standard__min']
            comparaison.prix_bus = prix_min
        else:
            # Prix par défaut si aucun trajet n'est trouvé
            comparaison.prix_bus = calculer_prix_service('bus_standard', 0, nombre_passagers)

        comparaison.prix_train = calculer_prix_service('train_standard', 50, nombre_passagers)

        return render(request, 'resultats.html', {'comparaison': comparaison})
    else:
        return render(request, 'accueil.html')

def train_search(request):
    """Vue pour afficher le formulaire de recherche de trains."""
    form = TrainSearchForm()
    return render(request, 'oncf_scraper/home.html', {'form': form})

def train_results(request):
    """Vue pour afficher les résultats de la recherche de trains."""
    # Récupérer les informations de recherche depuis la session
    search_info = request.session.get('train_search')
    
    if not search_info:
        messages.error(request, "Veuillez d'abord effectuer une recherche.")
        return redirect('reservation_train')
    
    try:
        # Récupérer les données de recherche
        depart_id = search_info.get('depart')
        destination_id = search_info.get('destination')
        date_str = search_info.get('date')
        heure_str = search_info.get('heure')
        nombre_passagers = search_info.get('nombre_passagers', 1)
        
        # Convertir les IDs en objets
        depart = TrainStation.objects.get(id=depart_id) if isinstance(depart_id, int) else depart_id
        destination = TrainStation.objects.get(id=destination_id) if isinstance(destination_id, int) else destination_id
        
        # Convertir la date et l'heure
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        heure = datetime.datetime.strptime(heure_str, '%H:%M').time()
        
        # Convertir l'heure en datetime pour la comparaison
        search_datetime = datetime.datetime.combine(date, heure)
        
        # Trouver le trajet correspondant
        route = TrainRoute.objects.get(
            departure_station=depart,
            arrival_station=destination
        )
        
        # Trouver les horaires disponibles pour ce trajet
        schedules = TrainSchedule.objects.filter(
            route=route,
            is_active=True
        )
        
        # Filtrer par jour de la semaine
        filtered_schedules = []
        for schedule in schedules:
            if schedule.is_available_on_date(date):
                filtered_schedules.append(schedule)
        
        # Convertir les horaires en format pour le template
        train_results = []
        for schedule in filtered_schedules:
            # Vérifier si l'heure de départ est après l'heure de recherche ou dans les 30 minutes avant
            departure_datetime = datetime.datetime.combine(date, schedule.departure_time)
            time_diff = (departure_datetime - search_datetime).total_seconds() / 60
            
            # Inclure les trains qui partent dans les 30 minutes avant l'heure de recherche ou après
            if time_diff >= -30:
                train_results.append({
                    "heure_depart": schedule.departure_time.strftime('%H:%M'),
                    "heure_arrivee": schedule.arrival_time.strftime('%H:%M'),
                    "duree": schedule.get_duration_display(),
                    "prix": f"{schedule.price} MAD",
                    "train_type": schedule.train_type.name,
                    "train_id": schedule.id
                })
        
        # Trier par heure de départ
        train_results.sort(key=lambda x: x["heure_depart"])
        
        if not train_results:
            messages.info(request, "Aucun train disponible pour cette recherche. Essayez une autre date ou heure.")
        
        # Préparer le contexte pour le template
        context = {
            'results': train_results,
            'search_params': {
                'depart': depart.name if hasattr(depart, 'name') else depart,
                'destination': destination.name if hasattr(destination, 'name') else destination,
                'date': date,
                'heure': heure,
                'nombre_passagers': nombre_passagers
            }
        }
        
        return render(request, 'Safariyat/train_results.html', context)
        
    except Exception as e:
        logger.error(f"Erreur dans train_results: {str(e)}")
        messages.error(request, f"Une erreur s'est produite: {str(e)}")
        return redirect('reservation_train')

def train_seats_payment(request, train_id):
    """Vue pour afficher les places disponibles et le paiement pour un train sélectionné."""
    try:
        # Récupérer l'horaire du train
        schedule = TrainSchedule.objects.get(id=train_id)
        
        # Récupérer les informations de recherche depuis la session
        search_info = request.session.get('train_search')
        if not search_info:
            messages.error(request, "Informations de recherche manquantes.")
            return redirect('reservation_train')
        
        date_str = search_info.get('date')
        nombre_passagers = search_info.get('nombre_passagers', 1)
        
        # Convertir la date
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Générer des places disponibles (exemple simplifié)
        # Dans une implémentation réelle, vous récupéreriez les places disponibles depuis la base de données
        total_seats = 60  # Exemple: 60 places au total
        booked_seats = []  # Exemple: aucune place réservée
        
        # Générer la liste des places disponibles
        available_seats = []
        for i in range(1, total_seats + 1):
            if i not in booked_seats:
                # Déterminer la classe (1ère ou 2nde)
                seat_class = "1ère classe" if i <= 20 else "2nde classe"
                # Déterminer le prix (plus cher pour la 1ère classe)
                price = float(schedule.price) * 1.5 if i <= 20 else float(schedule.price)
                
                available_seats.append({
                    'number': i,
                    'class': seat_class,
                    'price': price,
                    'position': 'Fenêtre' if i % 4 in [1, 4] else 'Couloir'
                })
        
        if request.method == 'POST':
            # Traiter la sélection de place et le paiement
            seat_number = request.POST.get('seat_number')
            payment_method = request.POST.get('payment_method', 'card')
            
            if not seat_number:
                messages.error(request, "Veuillez sélectionner une place.")
                return redirect('train_seats_payment', train_id=train_id)
            
            # Stocker les informations dans la session
            request.session['train_id'] = train_id
            request.session['seat_number'] = seat_number
            request.session['payment_method'] = payment_method
            
            # Rediriger vers la page de confirmation
            return redirect('train_confirmation')
        
        # Préparer le contexte pour le template
        context = {
            'schedule': schedule,
            'date': date,
            'available_seats': available_seats,
            'route': schedule.route,
            'train_type': schedule.train_type,
            'nombre_passagers': nombre_passagers
        }
        
        return render(request, 'Safariyat/train_seats_payment.html', context)
        
    except TrainSchedule.DoesNotExist:
        messages.error(request, "Le train sélectionné n'existe pas ou n'est plus disponible.")
        return redirect('reservation_train')
    except Exception as e:
        logger.error(f"Erreur dans train_seats_payment: {str(e)}")
        messages.error(request, f"Une erreur s'est produite: {str(e)}")
        return redirect('reservation_train')

# Configurer le logger
logger = logging.getLogger(__name__)
@login_required
def train_confirmation(request):
    """Vue pour confirmer une réservation de train."""
    # Récupérer les informations de la session
    train_id = request.session.get('train_id')
    seat_number = request.session.get('seat_number')
    payment_method = request.session.get('payment_method', 'card')
    search_info = request.session.get('train_search', {})
    
    # Ajouter des logs pour déboguer
    logger.info(f"train_confirmation appelé - train_id: {train_id}, seat_number: {seat_number}")
    logger.info(f"Méthode de requête: {request.method}")
    logger.info(f"POST data: {request.POST}")
    
    if not train_id or not seat_number:
        messages.error(request, "Informations de réservation manquantes.")
        return redirect('reservation_train')
    
    try:
        # Récupérer l'horaire du train
        schedule = TrainSchedule.objects.get(id=train_id)
        logger.info(f"Schedule trouvé: {schedule}")
        
        # Récupérer ou créer le client
        client = get_or_create_client(request.user)
        if not client:
            messages.error(request, "Vous devez être connecté pour effectuer une réservation.")
            return redirect('login')
        
        logger.info(f"Client trouvé: {client.id} - {client.first_name} {client.last_name}")
        
        # Récupérer les informations de recherche
        date_str = search_info.get('date')
        nombre_passagers = int(search_info.get('nombre_passagers', 1))
        
        # Convertir la date
        date_voyage = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Déterminer la classe en fonction du numéro de siège (exemple simplifié)
        classe = 'premiere' if int(seat_number) <= 20 else 'seconde'
        
        # Calculer le prix
        prix = calculate_train_price(float(schedule.price), classe, nombre_passagers)
        
        if request.method == 'POST' and 'confirm_reservation' in request.POST:
            logger.info("Création de la réservation...")
            
            # Créer la réservation
            reservation = TrainReservation(
                client=client,
                depart=schedule.route.departure_station.name if hasattr(schedule.route.departure_station, 'name') else "Départ",
                destination=schedule.route.arrival_station.name if hasattr(schedule.route.arrival_station, 'name') else "Destination",
                date_voyage=date_voyage,
                nb_passagers=nombre_passagers,
                classe=classe,
                prix=prix,
                statut='confirmé',
                numero_siege=seat_number,
                train_schedule=schedule
            )
            
            # Sauvegarder explicitement la réservation
            reservation.save()
            
            # Ajouter des points de fidélité au client
            from .utils import mettre_a_jour_points_fidelite
            points_ajoutes = mettre_a_jour_points_fidelite(client, prix)
            logger.info(f"Points de fidélité ajoutés: {points_ajoutes}")
            
            # Vérifier que la réservation a bien été créée
            try:
                saved_reservation = TrainReservation.objects.get(id=reservation.id)
                logger.info(f"Réservation créée avec succès: ID={saved_reservation.id}, Client={client.id}, Statut={saved_reservation.statut}")
            except TrainReservation.DoesNotExist:
                logger.error("La réservation n'a pas été sauvegardée correctement!")
            
            # Créer également une entrée dans la table Reservation pour l'historique global
            try:
                Reservation.objects.create(
                    client=client,
                    travel_date=datetime.datetime.combine(date_voyage, schedule.departure_time),
                    travel_type='train',
                    origin=reservation.depart,
                    destination=reservation.destination,
                    amount=prix
                )
                logger.info("Entrée créée dans la table Reservation")
            except Exception as e:
                logger.error(f"Erreur lors de la création de l'entrée dans Reservation: {str(e)}")
            
            # Nettoyer la session
            for key in ['train_id', 'seat_number', 'payment_method', 'train_search']:
                if key in request.session:
                    del request.session[key]
            
            # Rediriger vers la page de succès
            messages.success(request, f"Votre réservation de train a été confirmée avec succès! Vous avez gagné {points_ajoutes} points de fidélité.")
            return redirect('historique_reservations')
        
        # Préparer le contexte pour le template
        context = {
            'schedule': schedule,
            'date_voyage': date_voyage,
            'seat_number': seat_number,
            'classe': 'Première classe' if classe == 'premiere' else 'Seconde classe',
            'nombre_passagers': nombre_passagers,
            'prix': prix,
            'payment_method': payment_method
        }
        
        return render(request, 'Safariyat/train_confirmation.html', context)
        
    except TrainSchedule.DoesNotExist:
        messages.error(request, "Le train sélectionné n'existe pas ou n'est plus disponible.")
        return redirect('reservation_train')
    except Exception as e:
        logger.error(f"Erreur dans train_confirmation: {str(e)}")
        logger.error(traceback.format_exc())
        messages.error(request, f"Une erreur s'est produite: {str(e)}")
        return redirect('reservation_train')

def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            # Redirection vers la page précédente si disponible, sinon vers la page d'accueil
            next_page = request.GET.get('next', 'choix_transport')
            return redirect(next_page)
        else:
            messages.error(request, "Email ou mot de passe incorrect.")
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('accueil')

def password_reset(request):
    if request.method == "POST":
        email = request.POST["email"]
        user = User.objects.filter(email=email).first()
        if user:
            send_mail(
                "Réinitialisation du mot de passe",
                "Cliquez sur le lien pour réinitialiser votre mot de passe.",
                "admin@safariyat.com",
                [email],
                fail_silently=False,
            )
            messages.success(request, "Email de réinitialisation envoyé.")
        else:
            messages.error(request, "Aucun compte trouvé avec cet email.")
        return redirect("login")
    return render(request, "password_reset.html")

def choix_transport(request):
    return render(request, 'choix_transport.html')

# Modify your about view in views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ContactForm

def about(request):
    """
    View for the about page with contact form
    """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Votre message a été envoyé avec succès. Nous vous répondrons dans les plus brefs délais.")
            return redirect('about')
    else:
        form = ContactForm()
    
    return render(request, 'about.html', {'form': form})

def reservation_view(request):
    return render(request, 'reservation_bus.html')

@login_required
def historique_reservations(request):
    """Vue pour afficher l'historique des réservations d'un client."""
    try:
        # Récupérer le client associé à l'utilisateur connecté
        client = get_or_create_client(request.user)
        
        if not client:
            messages.error(request, "Vous devez être connecté pour accéder à votre historique.")
            return redirect('login')
        
        # Ajouter un log pour le débogage
        logger.info(f"Récupération des réservations pour le client ID: {client.id}")
        
        # Récupérer les réservations de taxi
        reservations_taxi = TaxiReservation.objects.filter(client=client).order_by('-date')
        logger.info(f"Nombre de réservations de taxi: {reservations_taxi.count()}")
        
        # Récupérer les réservations de bus
        reservations_bus = AutobusReservation.objects.filter(client=client).order_by('-date_voyage')
        logger.info(f"Nombre de réservations de bus: {reservations_bus.count()}")
        
        # Récupérer les réservations de train
        logger.info(f"Récupération des réservations de train pour le client ID: {client.id}")
        reservations_train = TrainReservation.objects.filter(client=client).order_by('-date_voyage')
        
        # Ajouter des logs détaillés pour les réservations de train
        logger.info(f"SQL Query pour les réservations de train: {str(TrainReservation.objects.filter(client=client).query)}")
        logger.info(f"Nombre de réservations de train: {reservations_train.count()}")
        
        for res in reservations_train:
            logger.info(f"Train reservation: ID={res.id}, Date={res.date_voyage}, Status={res.statut}")
        
        # Calculer les totaux
        total_taxi = reservations_taxi.count()
        total_bus = reservations_bus.count()
        total_train = reservations_train.count()
        total = total_taxi + total_bus + total_train
        
        # Préparer le contexte pour le template
        context = {
            'reservations_taxi': reservations_taxi,
            'reservations_bus': reservations_bus,
            'reservations_train': reservations_train,
            'total_taxi': total_taxi,
            'total_bus': total_bus,
            'total_train': total_train,
            'total': total
        }
        
        return render(request, 'Safariyat/historique.html', context)
        
    except Exception as e:
        logger.error(f"Erreur dans historique_reservations: {str(e)}")
        logger.error(traceback.format_exc())
        messages.error(request, f"Une erreur s'est produite: {str(e)}")
        return redirect('accueil')

@login_required
def create_client_profile(request):
    """
    View to manually create a Client profile for the logged-in user
    """
    # Check if the user already has a client profile
    try:
        client = Client.objects.get(user=request.user)
        messages.info(request, "Vous avez déjà un profil client.")
        return redirect('accueil')
    except Client.DoesNotExist:
        # If no client profile exists, create one
        if request.method == 'POST':
            first_name = request.POST.get('first_name', request.user.first_name)
            last_name = request.POST.get('last_name', request.user.last_name)
            email = request.POST.get('email', request.user.email)
            phone_number = request.POST.get('phone_number', '')
            
            # Create the client profile
            client = Client.objects.create(
                user=request.user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number
            )
            
            # Create a ClientFidelite record for the new client
            ClientFidelite.objects.create(
                client=client,
                points=0,
                niveau='bronze'
            )
            
            messages.success(request, "Votre profil client a été créé avec succès!")
            return redirect('accueil')
        
        # Display the form to create a client profile
        return render(request, 'Safariyat/create_client_profile.html', {
            'user': request.user
        })

@login_required
def profil_fidelite(request):
    """
    Affiche le profil de fidélité de l'utilisateur connecté et met à jour ses points
    en fonction de l'historique des réservations
    """
    # Récupérer ou créer le client associé à l'utilisateur
    client = get_or_create_client(request.user)
    
    # Récupérer ou créer le profil de fidélité
    fidelite, created = ClientFidelite.objects.get_or_create(
        client=client,
        defaults={'points': 0, 'niveau': 'bronze', 'date_inscription': datetime.date.today()}
    )
    
    # Récupérer l'historique des réservations
    reservations_taxi = TaxiReservation.objects.filter(client=client).order_by('-date')
    reservations_bus = AutobusReservation.objects.filter(client=client).order_by('-date_voyage')
    reservations_train = TrainReservation.objects.filter(client=client).order_by('-date_voyage')
    
    # Calculer le nombre total de réservations
    total_reservations = reservations_taxi.count() + reservations_bus.count() + reservations_train.count()
    
    # Calculer le total des points à partir de l'historique des réservations
    total_points = 0
    
    # Ajouter les points des réservations de taxi
    for reservation in reservations_taxi:
        if hasattr(reservation, 'prix_total') and reservation.prix_total:
            total_points += int(reservation.prix_total)
    
    # Ajouter les points des réservations de bus
    for reservation in reservations_bus:
        if hasattr(reservation, 'prix_total') and reservation.prix_total:
            total_points += int(reservation.prix_total)
    
    # Ajouter les points des réservations de train
    for reservation in reservations_train:
        if hasattr(reservation, 'prix') and reservation.prix:
            total_points += int(reservation.prix)
    
    # Mettre à jour les points du client si nécessaire
    if total_points > fidelite.points:
        fidelite.points = total_points
        
        # Mettre à jour le niveau en fonction des points
        if total_points >= 1000:
            fidelite.niveau = 'platine'
        elif total_points >= 500:
            fidelite.niveau = 'or'
        elif total_points >= 200:
            fidelite.niveau = 'argent'
        else:
            fidelite.niveau = 'bronze'
            
        # Sauvegarder les modifications
        fidelite.save()
    
    # Calculer les pourcentages pour les barres de progression
    points = fidelite.points or 0
    
    # Déterminer le niveau et calculer le pourcentage approprié
    if fidelite.niveau == 'bronze':
        max_points = 200
        pourcentage = min(100, int((points / max_points) * 100)) if max_points > 0 else 0
    elif fidelite.niveau == 'argent':
        max_points = 500
        pourcentage = min(100, int((points / max_points) * 100)) if max_points > 0 else 0
    elif fidelite.niveau == 'or':
        max_points = 1000
        pourcentage = min(100, int((points / max_points) * 100)) if max_points > 0 else 0
    else:
        max_points = 1000
        pourcentage = 100
    
    # Calculer la réduction en fonction du niveau
    if hasattr(fidelite, 'obtenir_reduction'):
        reduction = fidelite.obtenir_reduction()
    else:
        # Calcul de réduction par défaut si la méthode n'existe pas
        if fidelite.niveau == 'bronze':
            reduction = 5
        elif fidelite.niveau == 'argent':
            reduction = 10
        elif fidelite.niveau == 'or':
            reduction = 15
        else:  # platine
            reduction = 20
    
    # Préparer le contexte
    context = {
        'client': client,
        'fidelite': fidelite,
        'total_reservations': total_reservations,
        'reservations_taxi': reservations_taxi,
        'reservations_bus': reservations_bus,
        'reservations_train': reservations_train,
        'reduction': reduction,
        'pourcentage': pourcentage,
        'max_points': max_points,
        'total_points': total_points  # Ajouter le total calculé pour le débogage
    }
    
    return render(request, 'Safariyat/profil_fidelite.html', context)


def signup(request):
    if request.method == "POST":
        nom = request.POST.get("nom", "")
        prenom = request.POST.get("prenom", "")
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        telephone = request.POST.get("telephone", "")
        
        try:
            # Create the user
            user = User.objects.create_user(
                username=email, 
                email=email, 
                password=password, 
                first_name=prenom,
                last_name=nom
            )
            
            # Create the associated Client profile
            client = Client.objects.create(
                user=user,
                first_name=prenom,
                last_name=nom,
                email=email,
                phone_number=telephone
            )
            
            # Create a ClientFidelite record for the new client
            ClientFidelite.objects.create(
                client=client,
                points=0,
                niveau='bronze'
            )
            
            messages.success(request, "Compte créé avec succès ! Vous pouvez vous connecter.")
            return redirect("login")
        except Exception as e:
            # If there's an error, delete the user if it was created
            if 'user' in locals():
                user.delete()
            messages.error(request, f"Erreur lors de la création du compte: {str(e)}")
    
    return render(request, "signup.html")

def ensure_client_profile(user):
    """
    Utility function to check if a user has a client profile and create one if not
    """
    try:
        return Client.objects.get(user=user)
    except Client.DoesNotExist:
        # Create a new client profile
        client = Client.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone_number=""
        )
        
        # Create a ClientFidelite record
        ClientFidelite.objects.create(
            client=client,
            points=0,
            niveau='bronze'
        )
        
        return client

def reservation_train(request):
    """
    Vue pour la réservation de billets de train.
    Affiche un formulaire unique de réservation.
    """
    if request.method == 'POST':
        form = TrainSearchForm(request.POST)
        if form.is_valid():
            depart = form.cleaned_data['depart']
            destination = form.cleaned_data['destination']
            date = form.cleaned_data['date']
            heure = form.cleaned_data['heure']
            nombre_passagers = form.cleaned_data['nombre_passagers']
            
            # Stocker les informations dans la session
            request.session['train_search'] = {
                'depart': depart.id if hasattr(depart, 'id') else depart,
                'destination': destination.id if hasattr(destination, 'id') else destination,
                'date': date.strftime('%Y-%m-%d'),
                'heure': heure.strftime('%H:%M'),
                'nombre_passagers': nombre_passagers
            }
            
            # Rediriger vers la page des résultats
            return redirect('train_results')
    else:
        form = TrainSearchForm()
    
    return render(request, 'Safariyat/reservation_train.html', {'form': form})

def reservation_bus(request):
    """
    Vue pour la réservation d'autobus, avec possibilité de spécifier la compagnie
    """
    # Récupérer l'ID de la compagnie depuis les paramètres GET
    compagnie_id = request.GET.get('compagnie')
    compagnie_nom = 'Toutes'
    
    # Si une compagnie est spécifiée, récupérer son nom
    if compagnie_id:
        try:
            compagnie = CompagnieTransport.objects.get(id=compagnie_id)
            compagnie_nom = compagnie.nom
        except CompagnieTransport.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            # Récupérer les données du formulaire
            depart = form.cleaned_data['ville_depart']
            destination = form.cleaned_data['ville_arrivee']
            date_depart = form.cleaned_data['date_depart']
            date_retour = form.cleaned_data['date_retour']
            passagers = form.cleaned_data['nombre_places']
            
            # Stocker les données dans la session pour les récupérer dans la vue des disponibilités
            request.session['recherche'] = {
                'compagnie': compagnie_nom,
                'depart': depart,
                'destination': destination,
                'date_depart': date_depart.strftime('%d/%m/%Y'),
                'date_retour': date_retour.strftime('%d/%m/%Y'),
                'passagers': passagers
            }
            
            # Rediriger vers la page des disponibilités
            return redirect('disponibilites')
    else:
        form = ReservationForm()

    return render(request, 'Safariyat/reservation_bus.html', {
        'form': form,
        'compagnie_nom': compagnie_nom
    })


def compagnies(request):
    """
    Vue pour afficher la liste des compagnies d'autobus disponibles
    """
    # Récupérer toutes les compagnies actives
    compagnies_list = CompagnieTransport.objects.filter(est_actif=True)
    
    # Passer les compagnies au template
    context = {
        'compagnies': compagnies_list,
        'title': 'Nos compagnies partenaires'
    }
    
    return render(request, 'Safariyat/compagnies.html', context)

def choix_compagnie(request):
    # Récupérer toutes les compagnies actives
    compagnies_list = CompagnieTransport.objects.filter(est_actif=True)
    return render(request, 'Safariyat/choix_compagnie.html', {'compagnies': compagnies_list})

def disponibilites(request):
    """
    Vue pour afficher les disponibilités d'autobus en fonction des critères de recherche
    """
    # Récupérer les données de recherche depuis la session
    recherche = request.session.get('recherche', {})
    
    if not recherche:
        # Si aucune recherche n'a été effectuée, rediriger vers la page de réservation
        return redirect('reservation_bus')
    
    # Récupérer les critères de recherche
    compagnie = recherche.get('compagnie', 'Toutes')
    depart = recherche.get('depart', '')
    destination = recherche.get('destination', '')
    date_depart = recherche.get('date_depart', '')
    date_retour = recherche.get('date_retour', '')
    passagers = recherche.get('passagers', 1)
    
    # Rechercher les disponibilités
    disponibilites = rechercher_disponibilites(compagnie, depart, destination, date_depart, date_retour, passagers)
    
    # Passer les données au template
    context = {
        'compagnie': compagnie,
        'depart': depart,
        'destination': destination,
        'date_depart': date_depart,
        'date_retour': date_retour,
        'passagers': passagers,
        'disponibilites': disponibilites
    }
    
    return render(request, 'Safariyat/disponibilites.html', context)

def send_receipt(user, reservation_details):
    subject = "Votre reçu Safariyat"
    message = f"Merci pour votre réservation !\n\nDétails de votre réservation : {reservation_details}"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])



def send_thank_you_email(user, discount_amount):
    subject = "Merci pour votre fidélité"
    message = f"Merci pour votre fidélité !\nVous avez reçu une réduction de {discount_amount} sur votre dernière réservation."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

def rechercher_disponibilites(compagnie, depart, destination, date_depart, date_retour, passagers):
    """
    Fonction pour rechercher les disponibilités d'autobus en fonction des critères
    """
    # Log des paramètres de recherche pour le débogage
    logger.info(f"Recherche: compagnie={compagnie}, depart={depart}, destination={destination}, date={date_depart}, passagers={passagers}")
    
    # Convertir la date de départ en objet date
    try:
        date_depart_obj = datetime.datetime.strptime(date_depart, '%d/%m/%Y').date()
        jour_semaine = date_depart_obj.strftime('%a').lower()  # Obtenir le jour de la semaine (lun, mar, etc.)
        logger.info(f"Date convertie: {date_depart_obj}, jour: {jour_semaine}")
    except ValueError as e:
        # Si la date n'est pas valide, retourner une liste vide
        logger.error(f"Erreur de conversion de date: {e}")
        return []
    
    # Récupérer tous les trajets actifs
    trajets = TrajetAutobus.objects.filter(est_actif=True)
    logger.info(f"Nombre total de trajets actifs: {trajets.count()}")
    
    # Filtrer par ville de départ et d'arrivée (insensible à la casse)
    if depart:
        trajets = trajets.filter(ville_depart__iexact=depart)
        logger.info(f"Après filtre départ: {trajets.count()} trajets")
    
    if destination:
        trajets = trajets.filter(ville_arrivee__iexact=destination)
        logger.info(f"Après filtre destination: {trajets.count()} trajets")
    
    # Filtrer par compagnie si spécifiée et différente de "Toutes"
    if compagnie and compagnie.lower() != 'toutes':
        trajets = trajets.filter(autobus__compagnie__nom__iexact=compagnie)
        logger.info(f"Après filtre compagnie: {trajets.count()} trajets")
    
    # Filtrer par nombre de places disponibles
    if passagers:
        try:
            passagers_int = int(passagers)
            trajets = trajets.filter(places_disponibles__gte=passagers_int)
            logger.info(f"Après filtre passagers: {trajets.count()} trajets")
        except (ValueError, TypeError):
            logger.error(f"Erreur de conversion du nombre de passagers: {passagers}")
    
    # Préparer les résultats
    disponibilites = []
    for trajet in trajets:
        disponibilites.append({
            'id': trajet.id,
            'compagnie': trajet.autobus.compagnie.nom,
            'numero_bus': trajet.autobus.numero_bus,
            'ville_depart': trajet.ville_depart,
            'ville_arrivee': trajet.ville_arrivee,
            'heure_depart': trajet.heure_depart,
            'heure_arrivee': trajet.heure_arrivee,
            'duree': trajet.duree,
            'prix': trajet.prix_standard,
            'places_disponibles': trajet.places_disponibles,
            'type': trajet.autobus.type_bus,
            'est_climatise': trajet.autobus.est_climatise,
            'wifi_disponible': trajet.autobus.wifi_disponible
        })
    
    logger.info(f"Nombre de résultats trouvés: {len(disponibilites)}")
    return disponibilites


def reserver(request, trajet_id):
    """
    Vue pour réserver un trajet et rediriger vers la page de paiement
    """
    # Récupérer le trajet
    try:
        trajet = TrajetAutobus.objects.get(id=trajet_id)
    except TrajetAutobus.DoesNotExist:
        messages.error(request, "Ce trajet n'existe pas ou n'est plus disponible.")
        return redirect('reservation_bus')
    
    # Récupérer les informations de recherche depuis la session
    recherche = request.session.get('recherche', {})
    passagers = recherche.get('passagers', 1)
    date_depart = recherche.get('date_depart', '')
    
    # Créer une réservation temporaire
    reservation = Reservation(
        utilisateur=request.user if request.user.is_authenticated else None,
        trajet=trajet,
        date_voyage=datetime.datetime.strptime(date_depart, '%d/%m/%Y').date() if date_depart else None,
        nombre_passagers=passagers,
        prix_total=trajet.prix_standard * passagers,
        statut='en_attente'
    )
    reservation.save()
    
    # Stocker l'ID de réservation dans la session
    request.session['reservation_id'] = reservation.id
    
    # Rediriger vers la page de paiement
    return redirect('paiement')

def reserver_taxi(request):
    """
    Vue pour afficher le formulaire de réservation de taxi
    """
    context = {
        'today_date': datetime.date.today().strftime('%Y-%m-%d')
    }
    return render(request, 'Safariyat/taxi_reservation.html', context)

def taxi_confirmation(request):
    """
    Vue pour traiter la soumission du formulaire de réservation de taxi
    """
    if request.method == 'POST':
        # Récupérer les données du formulaire
        depart = request.POST.get('depart')
        destination = request.POST.get('destination')
        date_str = request.POST.get('date')
        heure_str = request.POST.get('heure')
        nombre_passagers = request.POST.get('nombre_passagers')
        type_taxi = request.POST.get('type_taxi')
        email = request.POST.get('email')
        
        # Ajouter des logs pour déboguer
        logger.info(f"Données reçues: départ={depart}, destination={destination}, date={date_str}, heure={heure_str}")
        
        try:
            # Convertir la date
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Calculer le prix en utilisant la fonction utilitaire
            prix = calculer_prix_service(f'taxi_{type_taxi}', 0, int(nombre_passagers))
            
            # Créer et sauvegarder la réservation
            reservation = TaxiReservation(
                depart=depart,
                destination=destination,
                date=date_obj,
                heure=heure_str,
                nombre_passagers=int(nombre_passagers),
                type_taxi=type_taxi,
                statut='confirmee',  # Statut confirmé
                ticket_envoye=False,  # Initialiser le champ de suivi des tickets
                prix_total=prix  # Utiliser le prix calculé
            )
            
            # Si l'email est fourni, l'enregistrer
            if email:
                reservation.email_passager = email
                
            # Si l'utilisateur est connecté, associer la réservation à son compte
            if request.user.is_authenticated:
                client = get_or_create_client(request.user)
                reservation.client = client
                
            reservation.save()
            
            logger.info(f"Réservation créée avec ID: {reservation.id}")
            
            # Stocker l'ID dans la session
            request.session['taxi_reservation_id'] = reservation.id
            
            # Rediriger vers la page de confirmation
            return redirect('taxi_confirmation_page')
            
        except Exception as e:
            logger.error(f"ERREUR: {str(e)}")
            logger.error(traceback.format_exc())
            messages.error(request, f"Une erreur s'est produite: {str(e)}")
            return redirect('reserver_taxi')
    
    # Si la méthode n'est pas POST, rediriger vers le formulaire
    return redirect('reserver_taxi')

def get_taxi_price(type_taxi, nombre_passagers):
    """
    Calcule le prix du taxi en fonction du type et du nombre de passagers
    en utilisant le modèle Prix
    """
    return calculer_prix_service(f'taxi_{type_taxi}', 0, int(nombre_passagers))

def taxi_confirmation_page(request):
    """
    Vue pour afficher la page de confirmation après réservation de taxi
    """
    # Récupérer l'ID de réservation depuis la session
    reservation_id = request.session.get('taxi_reservation_id')
    
    if not reservation_id:
        messages.error(request, "Aucune réservation trouvée.")
        return redirect('reserver_taxi')
    
    try:
        # Récupérer la réservation
        reservation = TaxiReservation.objects.get(id=reservation_id)
        
        # Préparer le contexte
        context = {
            'reservation': reservation,
            'prix': reservation.prix_total
        }
        
        # Envoyer le ticket par email après avoir affiché la page de confirmation
        if hasattr(reservation, 'email_passager') and reservation.email_passager:
            try:
                # Utiliser un thread pour ne pas bloquer la réponse
                thread = Thread(target=send_ticket_email, args=(reservation, reservation.email_passager))
                thread.start()
                messages.success(request, "Un ticket sera envoyé à votre adresse email.")
            except Exception as e:
                messages.warning(request, f"Impossible d'envoyer le ticket par email: {str(e)}")
        
        # Nettoyer la session
        if 'taxi_reservation_id' in request.session:
            del request.session['taxi_reservation_id']
        
        return render(request, 'Safariyat/taxi_confirmation.html', context)
        
    except TaxiReservation.DoesNotExist:
        messages.error(request, "La réservation demandée n'existe pas.")
        return redirect('reserver_taxi')

def confirmation_finale(request):
    """
    Vue pour la page de confirmation finale après paiement
    """
    if request.method == 'POST':
        # Récupérer la méthode de paiement depuis le formulaire
        payment_method = request.POST.get('payment_method', 'card')
        email = request.POST.get('email')
        nom_complet = request.POST.get('nom_complet') or request.POST.get('nom_carte')
        telephone = request.POST.get('telephone')
        
        # Récupérer les informations de la session
        trajet_id = request.session.get('trajet_id')
        nombre_passagers = request.session.get('nombre_passagers', 1)
        date_voyage = request.session.get('date_voyage', datetime.datetime.now().strftime('%d/%m/%Y'))
        
        try:
            # Récupérer les informations du trajet
            trajet = TrajetAutobus.objects.get(id=trajet_id) if trajet_id else None
            
            if trajet:
                # Calculer le prix en utilisant la fonction utilitaire
                prix_unitaire = calculer_prix_service('bus_standard', 0, 1)
                prix_total = prix_unitaire * int(nombre_passagers)
                
                # Créer une réservation d'autobus
                reservation = AutobusReservation(
                    trajet=trajet,
                    date_voyage=datetime.datetime.strptime(date_voyage, '%d/%m/%Y').date(),
                    nombre_passagers=int(nombre_passagers),
                    prix_total=prix_total,
                    nom_passager=nom_complet,
                    email_passager=email,
                    telephone_passager=telephone,
                    statut='confirmee' if payment_method == 'card' else 'en_attente',
                    methode_paiement=payment_method
                )
                
                # Si l'utilisateur est authentifié, associer la réservation à son compte
                if request.user.is_authenticated:
                    client, created = Client.objects.get_or_create(
                        user=request.user,
                        defaults={
                            'first_name': request.user.first_name,
                            'last_name': request.user.last_name,
                            'email': request.user.email,
                            'phone_number': telephone or ''
                        }
                    )
                    reservation.client = client
                
                # Enregistrer la réservation
                reservation.save()
                
                # Mettre à jour le nombre de places disponibles
                trajet.places_disponibles -= int(nombre_passagers)
                trajet.save()
                
                # Créer également une entrée dans la table Reservation pour l'historique
                if request.user.is_authenticated and hasattr(request.user, 'client'):
                    Reservation.objects.create(
                        client=request.user.client,
                        travel_date=datetime.datetime.combine(
                            reservation.date_voyage,
                            datetime.datetime.strptime(trajet.heure_depart.strftime('%H:%M'), '%H:%M').time()
                        ),
                        travel_type='auto-bus',
                        origin=trajet.ville_depart,
                        destination=trajet.ville_arrivee,
                        amount=reservation.prix_total
                    )
                
                # Préparer le contexte pour le template
                context = {
                    'reservation_id': reservation.id,
                    'trajet': {
                        'ville_depart': trajet.ville_depart,
                        'ville_arrivee': trajet.ville_arrivee,
                    },
                    'compagnie': {
                        'nom': trajet.autobus.compagnie.nom if hasattr(trajet, 'autobus') else "Safariyat"
                    },
                    'date_voyage': date_voyage,
                    'heure_depart': trajet.heure_depart.strftime('%H:%M') if hasattr(trajet, 'heure_depart') else "08:00",
                    'heure_arrivee': trajet.heure_arrivee.strftime('%H:%M') if hasattr(trajet, 'heure_arrivee') else "10:00",
                    'reservation': {
                        'nombre_passagers': nombre_passagers,
                    },
                    'prix': reservation.prix_total,
                    'payment_method': payment_method
                }
                
                # Envoyer le ticket par email après avoir affiché la page de confirmation
                if email:
                    try:
                        # Utiliser un thread pour ne pas bloquer la réponse
                        thread = Thread(target=send_ticket_email, args=(reservation, email))
                        thread.start()
                        messages.success(request, "Un ticket sera envoyé à votre adresse email.")
                    except Exception as e:
                        messages.warning(request, f"Impossible d'envoyer le ticket par email: {str(e)}")
                
                # Rendre le template de confirmation
                return render(request, 'Safariyat/confirmation_reservation.html', context)
            else:
                # Si aucun trajet n'est trouvé, afficher un message d'erreur
                messages.error(request, "Trajet introuvable. Veuillez réessayer.")
                return redirect('reservation_bus')
                
        except Exception as e:
            messages.error(request, f"Une erreur s'est produite: {str(e)}")
            return redirect('reservation_bus')
    else:
        # Si la méthode n'est pas POST, rediriger vers la page de réservation
        return redirect('reservation_bus')
    
def paiement(request):
    """
    Vue pour la page de paiement
    """
    # Récupérer les informations de la session
    trajet_id = request.session.get('trajet_id')
    compagnie_id = request.session.get('compagnie_id')
    nombre_passagers = request.session.get('nombre_passagers', 1)
    
    try:
        # Récupérer les informations du trajet et de la compagnie
        trajet = TrajetAutobus.objects.get(id=trajet_id) if trajet_id else None
        compagnie = CompagnieTransport.objects.get(id=compagnie_id) if compagnie_id else None
        
        # Calculer le prix unitaire et total en utilisant la fonction utilitaire
        prix_unitaire = calculer_prix_service('bus_standard', 0, 1) if trajet else 100
        prix_total = float(prix_unitaire) * int(nombre_passagers)
        
        # Générer une référence de commande unique
        reference_commande = f"CMD-{uuid.uuid4().hex[:8].upper()}"
        
        # Préparer le contexte pour le template
        context = {
            'trajet': trajet,
            'compagnie': compagnie,
            'nombre_passagers': nombre_passagers,
            'prix_unitaire': prix_unitaire,
            'prix_total': prix_total,
            'reference_commande': reference_commande,
            'reservation': {
                'nombre_passagers': nombre_passagers,
                'prix_total': prix_total,
                'date_voyage': request.session.get('date_voyage', datetime.datetime.now().strftime('%d/%m/%Y')),
            }
        }
        
        return render(request, 'Safariyat/paiement.html', context)
        
    except Exception as e:
        messages.error(request, f"Une erreur s'est produite: {str(e)}")
        return redirect('reservation_bus')

def reservation_confirmation(request):
    """
    Vue pour la page de confirmation de réservation
    Cette fonction récupère l'ID du bus depuis les paramètres de requête
    et redirige vers la page de paiement
    """
    # Récupérer l'ID du bus sélectionné
    bus_id = request.GET.get('bus_id')
    
    if not bus_id:
        messages.error(request, "Aucun bus sélectionné.")
        return redirect('reservation_bus')
    
    try:
        # Récupérer les informations du trajet
        trajet = TrajetAutobus.objects.get(id=bus_id)
        
        # Stocker les informations du trajet dans la session pour les récupérer dans la page de paiement
        request.session['trajet_id'] = trajet.id
        request.session['compagnie_nom'] = trajet.autobus.compagnie.nom
        request.session['ville_depart'] = trajet.ville_depart
        request.session['ville_arrivee'] = trajet.ville_arrivee
        request.session['heure_depart'] = trajet.heure_depart.strftime('%H:%M')
        request.session['heure_arrivee'] = trajet.heure_arrivee.strftime('%H:%M')
        request.session['prix'] = float(trajet.prix_standard)
        
        # Rediriger vers la page de paiement
        return redirect('paiement')
        
    except TrajetAutobus.DoesNotExist:
        messages.error(request, "Le trajet sélectionné n'existe pas ou n'est plus disponible.")
        return redirect('reservation_bus')


@login_required
def send_reservation_ticket(request, reservation_id):
    """
    Vue pour envoyer manuellement un ticket de réservation
    """
    # Vérifier si l'utilisateur est administrateur
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas les permissions nécessaires.")
        return redirect('accueil')
    
    # Récupérer la réservation
    try:
        # Essayer de trouver dans différents modèles de réservation
        reservation = None
        
        # Essayer TaxiReservation
        try:
            reservation = TaxiReservation.objects.get(id=reservation_id)
        except TaxiReservation.DoesNotExist:
            pass
        
        # Essayer AutobusReservation
        if not reservation:
            try:
                reservation = AutobusReservation.objects.get(id=reservation_id)
            except AutobusReservation.DoesNotExist:
                pass
        
        # Essayer TrainReservation
        if not reservation:
            try:
                reservation = TrainReservation.objects.get(id=reservation_id)
            except TrainReservation.DoesNotExist:
                pass
        
        if not reservation:
            messages.error(request, "Réservation introuvable.")
            return redirect('admin:index')
        
        # Récupérer l'email depuis la requête ou utiliser celui de la réservation
        email = request.POST.get('email')
        
        # Envoyer le ticket
        success, message = send_ticket_email(reservation, email)
        
        if success:
            messages.success(request, "Ticket envoyé avec succès.")
            # Mettre à jour le statut d'envoi du ticket
            reservation.ticket_envoye = True
            reservation.save(update_fields=['ticket_envoye'])
        else:
            messages.error(request, f"Erreur lors de l'envoi du ticket: {message}")
        
        # Rediriger vers l'admin
        if isinstance(reservation, TaxiReservation):
            return redirect('admin:Safariyat_taxireservation_change', reservation_id)
        elif isinstance(reservation, AutobusReservation):
            return redirect('admin:Safariyat_autobusreservation_change', reservation_id)
        elif isinstance(reservation, TrainReservation):
            return redirect('admin:Safariyat_trainreservation_change', reservation_id)
        else:
            return redirect('admin:index')
            
    except Exception as e:
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('admin:index')

def download_ticket(request, reservation_id, reservation_type):
    """
    Vue pour télécharger un ticket de réservation en PDF
    """
    # Vérifier si l'utilisateur est connecté
    if not request.user.is_authenticated:
        messages.error(request, "Vous devez être connecté pour télécharger un ticket.")
        return redirect('login')
    
    # Récupérer la réservation
    reservation = None
    
    if reservation_type == 'taxi':
        try:
            reservation = TaxiReservation.objects.get(id=reservation_id)
            # Vérifier que l'utilisateur a accès à cette réservation
            if hasattr(reservation, 'email_passager') and reservation.email_passager != request.user.email:
                messages.error(request, "Vous n'avez pas accès à ce ticket.")
                return redirect('historique_reservations')
        except TaxiReservation.DoesNotExist:
            messages.error(request, "Réservation introuvable.")
            return redirect('historique_reservations')
    
    elif reservation_type == 'bus':
        try:
            reservation = AutobusReservation.objects.get(id=reservation_id)
            # Vérifier que l'utilisateur a accès à cette réservation
            if hasattr(request.user, 'client') and reservation.client != request.user.client:
                messages.error(request, "Vous n'avez pas accès à ce ticket.")
                return redirect('historique_reservations')
        except AutobusReservation.DoesNotExist:
            messages.error(request, "Réservation introuvable.")
            return redirect('historique_reservations')
    
    elif reservation_type == 'train':
        try:
            reservation = TrainReservation.objects.get(id=reservation_id)
            # Vérifier que l'utilisateur a accès à cette réservation
            if hasattr(request.user, 'client') and reservation.client != request.user.client:
                messages.error(request, "Vous n'avez pas accès à ce ticket.")
                return redirect('historique_reservations')
        except TrainReservation.DoesNotExist:
            messages.error(request, "Réservation introuvable.")
            return redirect('historique_reservations')
    
    else:
        messages.error(request, "Type de réservation non valide.")
        return redirect('historique_reservations')
    
    # Générer le PDF
    pdf = generate_pdf_ticket(reservation)
    
    # Créer la réponse HTTP avec le PDF
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_reservation_{reservation_id}.pdf"'
    
    return response

@staff_member_required
def admin_historique_reservations(request):
    """
    Vue pour afficher l'historique des réservations (accessible uniquement aux administrateurs)
    """
    # Initialiser des listes pour chaque type de réservation
    reservations = []
    taxi_reservations = []
    bus_reservations = []
    train_reservations = []

    try:
        # Récupérer toutes les réservations (pas seulement celles de l'utilisateur connecté)
        # Réservations standard
        reservations = Reservation.objects.all().order_by('-travel_date')
        
        # Réservations de taxi
        taxi_reservations = TaxiReservation.objects.all().order_by('-date')
        
        # Réservations d'autobus
        bus_reservations = AutobusReservation.objects.all().order_by('-date_voyage')
        
        # Réservations de train
        train_reservations = TrainReservation.objects.all().order_by('-date_voyage')
        
    except Exception as e:
        # En cas d'erreur, afficher un message dans la console
        logger.error(f"Erreur lors de la récupération des réservations: {str(e)}")

    # Passer les données au template
    context = {
        'reservations': reservations,
        'taxi_reservations': taxi_reservations,
        'bus_reservations': bus_reservations,
        'train_reservations': train_reservations,
        'is_admin_view': True
    }

    return render(request, 'Safariyat/admin_historique.html', context)

@login_required
def annuler_reservation(request, type_reservation, reservation_id):
    """
    Permet à l'utilisateur d'annuler une réservation
    """
    # Récupérer la réservation en fonction du type
    reservation = None
    if type_reservation == 'taxi':
        reservation = get_object_or_404(TaxiReservation, id=reservation_id)
        # Vérifier que l'utilisateur est bien le propriétaire de la réservation
        if hasattr(request.user, 'client') and reservation.client != request.user.client:
            messages.error(request, "Vous n'êtes pas autorisé à annuler cette réservation.")
            return redirect('historique_reservations')
    elif type_reservation == 'bus':
        reservation = get_object_or_404(AutobusReservation, id=reservation_id)
        if hasattr(request.user, 'client') and reservation.client != request.user.client:
            messages.error(request, "Vous n'êtes pas autorisé à annuler cette réservation.")
            return redirect('historique_reservations')
    elif type_reservation == 'train':
        reservation = get_object_or_404(TrainReservation, id=reservation_id)
        if hasattr(request.user, 'client') and reservation.client != request.user.client:
            messages.error(request, "Vous n'êtes pas autorisé à annuler cette réservation.")
            return redirect('historique_reservations')
    else:
        messages.error(request, "Type de réservation non valide.")
        return redirect('historique_reservations')

    # Vérifier si la réservation peut être annulée
    peut_annuler, pourcentage_remboursement, message = reservation.peut_annuler()

    if not peut_annuler:
        messages.error(request, f"Impossible d'annuler cette réservation: {message}")
        return redirect('historique_reservations')

    if request.method == 'POST':
        form = AnnulationForm(request.POST)
        if form.is_valid():
            raison = form.cleaned_data['raison']
            
            # Créer une demande d'annulation
            modification = ModificationReservation(
                reservation_type=type_reservation,
                reservation_id=reservation_id,
                type_modification='annulation',
                raison=raison,
                statut='en_attente'
            )
            
            # Calculer le remboursement
            if type_reservation == 'taxi':
                montant_total = reservation.prix_total
            elif type_reservation == 'bus':
                montant_total = reservation.prix_total
            else:  # train
                montant_total = reservation.prix
            
            remboursement = (montant_total * pourcentage_remboursement) / 100
            modification.remboursement = remboursement
            
            # Enregistrer la demande
            modification.save()
            
            # Mettre à jour le statut de la réservation
            reservation.statut = 'annulée' if type_reservation == 'train' else 'annulee'
            reservation.save()
            
            messages.success(request, f"Votre demande d'annulation a été enregistrée. Remboursement prévu: {remboursement} DH ({pourcentage_remboursement}%).")
            return redirect('historique_reservations')
    else:
        form = AnnulationForm()

    context = {
        'form': form,
        'reservation': reservation,
        'type_reservation': type_reservation,
        'pourcentage_remboursement': pourcentage_remboursement,
        'message': message
    }

    return render(request, 'Safariyat/annuler_reservation.html', context)

@login_required
def modifier_reservation(request, type_reservation, reservation_id):
    """
    Permet à l'utilisateur de modifier une réservation
    """
    # Récupérer la réservation en fonction du type
    reservation = None
    if type_reservation == 'taxi':
        reservation = get_object_or_404(TaxiReservation, id=reservation_id)
        # Vérifier que l'utilisateur est bien le propriétaire de la réservation
        if hasattr(request.user, 'client') and reservation.client != request.user.client:
            messages.error(request, "Vous n'êtes pas autorisé à modifier cette réservation.")
            return redirect('historique_reservations')
    elif type_reservation == 'bus':
        reservation = get_object_or_404(AutobusReservation, id=reservation_id)
        if hasattr(request.user, 'client') and reservation.client != request.user.client:
            messages.error(request, "Vous n'êtes pas autorisé à modifier cette réservation.")
            return redirect('historique_reservations')
    elif type_reservation == 'train':
        reservation = get_object_or_404(TrainReservation, id=reservation_id)
        if hasattr(request.user, 'client') and reservation.client != request.user.client:
            messages.error(request, "Vous n'êtes pas autorisé à modifier cette réservation.")
            return redirect('historique_reservations')
    else:
        messages.error(request, "Type de réservation non valide.")
        return redirect('historique_reservations')

    # Vérifier si la réservation peut être modifiée (même logique que pour l'annulation)
    peut_annuler, pourcentage_remboursement, message = reservation.peut_annuler()

    if not peut_annuler:
        messages.error(request, f"Impossible de modifier cette réservation: {message}")
        return redirect('historique_reservations')

    if request.method == 'POST':
        form = ModificationForm(request.POST, type_reservation=type_reservation, instance=reservation)
        if form.is_valid():
            # Créer une demande de modification
            modification = ModificationReservation(
                reservation_type=type_reservation,
                reservation_id=reservation_id,
                type_modification='modification',
                raison=form.cleaned_data['raison'],
                statut='en_attente'
            )
            
            # Calculer les frais de modification (exemple: 10% du prix total)
            if type_reservation == 'taxi':
                montant_total = reservation.prix_total
            elif type_reservation == 'bus':
                montant_total = reservation.prix_total
            else:  # train
                montant_total = reservation.prix
            
            frais_modification = montant_total * 0.1  # 10% de frais
            modification.frais = frais_modification
            
            # Enregistrer la demande
            modification.save()
            
            # Mettre à jour la réservation avec les nouvelles données
            if type_reservation == 'taxi':
                if 'date' in form.cleaned_data:
                    reservation.date = form.cleaned_data['date']
                if 'heure' in form.cleaned_data:
                    reservation.heure = form.cleaned_data['heure']
                if 'nombre_passagers' in form.cleaned_data:
                    reservation.nombre_passagers = form.cleaned_data['nombre_passagers']
            elif type_reservation == 'bus':
                if 'date_voyage' in form.cleaned_data:
                    reservation.date_voyage = form.cleaned_data['date_voyage']
                if 'nombre_passagers' in form.cleaned_data:
                    reservation.nombre_passagers = form.cleaned_data['nombre_passagers']
            else:  # train
                if 'date_voyage' in form.cleaned_data:
                    reservation.date_voyage = form.cleaned_data['date_voyage']
                if 'nb_passagers' in form.cleaned_data:
                    reservation.nb_passagers = form.cleaned_data['nb_passagers']
            
            # Mettre à jour le statut
            reservation.statut = 'modifiée' if type_reservation == 'train' else 'modifiee'
            reservation.save()
            
            messages.success(request, f"Votre demande de modification a été enregistrée. Frais de modification: {frais_modification} DH.")
            return redirect('historique_reservations')
    else:
        form = ModificationForm(type_reservation=type_reservation, instance=reservation)

    context = {
        'form': form,
        'reservation': reservation,
        'type_reservation': type_reservation
    }

    return render(request, 'Safariyat/modifier_reservation.html', context)




# Modifiez la fonction services_locaux dans views.py
# Modifiez la fonction services_locaux dans views.py pour résoudre le problème d'affichage

def services_locaux(request):
    """
    Affiche les services de transport locaux disponibles
    """
    # Récupérer la ville depuis la requête ou utiliser une valeur par défaut
    ville = request.GET.get('ville', 'Casablanca')

    # Récupérer les services actifs pour cette ville
    # Ajout de logging pour déboguer
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Recherche de services pour la ville: {ville}")
    
    # Récupérer tous les services actifs
    services = ServiceTransportLocal.objects.filter(est_actif=True)
    logger.info(f"Nombre total de services actifs: {services.count()}")
    
    # Filtrer par ville
    services_ville = services.filter(ville__iexact=ville)
    logger.info(f"Nombre de services pour {ville}: {services_ville.count()}")

    # Regrouper les services par type
    services_par_type = {
        'taxi': services_ville.filter(type_service='taxi'),
        'bus': services_ville.filter(type_service='bus'),
        'train': services_ville.filter(type_service='train'),
        'vtc': services_ville.filter(type_service='vtc'),
        'autre': services_ville.filter(type_service='autre')
    }
    
    # Log pour chaque type de service
    for type_service, queryset in services_par_type.items():
        logger.info(f"Services de type {type_service}: {queryset.count()}")

    # Récupérer la liste des villes disponibles pour le filtre
    villes_disponibles = ServiceTransportLocal.objects.filter(est_actif=True).values_list('ville', flat=True).distinct()
    logger.info(f"Villes disponibles: {list(villes_disponibles)}")

    context = {
        'services_par_type': services_par_type,
        'ville_actuelle': ville,
        'villes_disponibles': villes_disponibles
    }

    return render(request, 'Safariyat/services_locaux.html', context)


# Configurer le logger
logger = logging.getLogger(__name__)

def reserver_porte_a_porte(request):
    """
    Vue pour gérer la réservation de transport porte-à-porte.
    Gère à la fois l'affichage du formulaire et son traitement.
    """
    # Récupérer la date d'aujourd'hui pour la validation du formulaire
    today = datetime.date.today()
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        adresse_depart = request.POST.get('adresse_depart')
        adresse_destination = request.POST.get('adresse_destination')
        date_str = request.POST.get('date')
        heure_str = request.POST.get('heure')
        nombre_passagers = request.POST.get('nombre_passagers', 1)
        bagages = request.POST.get('bagages', 0)
        commentaires = request.POST.get('commentaires', '')
        
        # Options de transport
        option_taxi = request.POST.get('option_taxi') == '1'
        option_bus = request.POST.get('option_bus') == '1'
        option_train = request.POST.get('option_train') == '1'
        
        # Validation des données
        if not all([adresse_depart, adresse_destination, date_str, heure_str]):
            messages.error(request, "Veuillez remplir tous les champs obligatoires.")
            return redirect('reserver_porte_a_porte')
        
        try:
            # Convertir la date et l'heure
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            heure_obj = datetime.datetime.strptime(heure_str, '%H:%M').time()
            
            # Créer un objet datetime combiné
            date_heure = datetime.datetime.combine(date_obj, heure_obj)
            
            # Créer une nouvelle réservation
            reservation = PorteAPorteReservation()
            reservation.adresse_depart = adresse_depart
            reservation.adresse_destination = adresse_destination
            reservation.date = date_heure
            reservation.nb_passagers = int(nombre_passagers)
            reservation.bagages = int(bagages)  # Make sure this line exists
            reservation.commentaire = commentaires
            
            # Si l'utilisateur est connecté, associer la réservation à son compte
            if request.user.is_authenticated:
                client = get_or_create_client(request.user)
                reservation.client = client
                logger.info(f"Réservation associée au client: {client.id}")
            
            # Sauvegarder la réservation
            reservation.save()
            logger.info(f"Réservation porte-à-porte créée avec ID: {reservation.id}")
            
            # Stocker l'ID de réservation en session pour l'étape suivante
            request.session['porte_a_porte_id'] = reservation.id
            
            # Stocker les données du formulaire dans la session pour les récupérer à l'étape suivante
            request.session['porte_a_porte'] = {
                'adresse_depart': adresse_depart,
                'adresse_destination': adresse_destination,
                'date': date_str,
                'heure': heure_str,
                'nombre_passagers': int(nombre_passagers),
                'bagages': int(bagages),
                'commentaires': commentaires,
                'option_taxi': option_taxi,
                'option_bus': option_bus,
                'option_train': option_train
            }
            
            # Message de succès
            messages.success(request, "Détails de réservation enregistrés avec succès!")
            
            # Rediriger vers l'étape suivante (sélection des services)
            return redirect('selectionner_services')
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la réservation: {str(e)}")
            messages.error(request, f"Une erreur s'est produite: {str(e)}")
            return redirect('reserver_porte_a_porte')
    
    # Contexte pour le template (GET request)
    context = {
        'today': today,
    }
    
    return render(request, 'Safariyat/reserver_porte_a_porte.html', context)

@login_required
def selectionner_services(request):
    """
    Permet de sélectionner les services de transport pour un trajet porte-à-porte
    """
    # Récupérer les informations de la session
    porte_a_porte = request.session.get('porte_a_porte')
    porte_a_porte_id = request.session.get('porte_a_porte_id')

    if not porte_a_porte or not porte_a_porte_id:
        messages.error(request, "Veuillez d'abord saisir les détails de votre trajet.")
        return redirect('reserver_porte_a_porte')
    
    # Vérifier que la réservation existe
    try:
        reservation = PorteAPorteReservation.objects.get(id=porte_a_porte_id)
    except PorteAPorteReservation.DoesNotExist:
        messages.error(request, "Réservation introuvable. Veuillez recommencer.")
        return redirect('reserver_porte_a_porte')

    # Récupérer les services disponibles
    services_taxi = ServiceTransportLocal.objects.filter(est_actif=True, type_service='taxi')
    services_bus = ServiceTransportLocal.objects.filter(est_actif=True, type_service='bus')

    if request.method == 'POST':
        # Récupérer les services sélectionnés
        service_depart_id = request.POST.get('service_depart')
        service_principal_id = request.POST.get('service_principal')
        service_arrivee_id = request.POST.get('service_arrivee')
        
        if not service_principal_id:
            messages.error(request, "Veuillez sélectionner au moins un service principal.")
            return render(request, 'Safariyat/selectionner_services.html', {
                'porte_a_porte': porte_a_porte,
                'services_taxi': services_taxi,
                'services_bus': services_bus
            })
        
        # Stocker les sélections dans la session
        porte_a_porte['service_depart_id'] = service_depart_id
        porte_a_porte['service_principal_id'] = service_principal_id
        porte_a_porte['service_arrivee_id'] = service_arrivee_id
        request.session['porte_a_porte'] = porte_a_porte
        
        # Mettre à jour la réservation avec les services sélectionnés
        try:
            # Enregistrer les IDs des services dans la base de données
            if service_depart_id:
                reservation.service_depart_id = int(service_depart_id)
            
            if service_principal_id:
                reservation.service_principal_id = int(service_principal_id)
            
            if service_arrivee_id:
                reservation.service_arrivee_id = int(service_arrivee_id)
            
            reservation.save(update_fields=['service_depart_id', 'service_principal_id', 'service_arrivee_id'])
            logger.info(f"Services sélectionnés pour la réservation {reservation.id}")
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des services: {str(e)}")
            messages.warning(request, "Les services ont été sélectionnés mais n'ont pas pu être enregistrés.")
        
        # Rediriger vers la page de confirmation
        return redirect('confirmer_porte_a_porte')

    context = {
        'porte_a_porte': porte_a_porte,
        'services_taxi': services_taxi,
        'services_bus': services_bus
    }

    return render(request, 'Safariyat/selectionner_services.html', context)

@login_required
def confirmer_porte_a_porte(request):
    """
    Affiche un récapitulatif et permet de confirmer la réservation porte-à-porte
    """
    # Récupérer les informations de la session
    porte_a_porte = request.session.get('porte_a_porte')
    porte_a_porte_id = request.session.get('porte_a_porte_id')

    if not porte_a_porte or not porte_a_porte_id:
        messages.error(request, "Veuillez d'abord saisir les détails de votre trajet.")
        return redirect('reserver_porte_a_porte')

    # Récupérer la réservation
    try:
        reservation = PorteAPorteReservation.objects.get(id=porte_a_porte_id)
    except PorteAPorteReservation.DoesNotExist:
        messages.error(request, "Réservation introuvable. Veuillez recommencer.")
        return redirect('reserver_porte_a_porte')

    # Récupérer les services sélectionnés
    service_depart = None
    service_principal = None
    service_arrivee = None

    if porte_a_porte.get('service_depart_id'):
        try:
            service_depart = ServiceTransportLocal.objects.get(id=porte_a_porte['service_depart_id'])
        except ServiceTransportLocal.DoesNotExist:
            pass

    if porte_a_porte.get('service_principal_id'):
        try:
            service_principal = ServiceTransportLocal.objects.get(id=porte_a_porte['service_principal_id'])
        except ServiceTransportLocal.DoesNotExist:
            pass

    if porte_a_porte.get('service_arrivee_id'):
        try:
            service_arrivee = ServiceTransportLocal.objects.get(id=porte_a_porte['service_arrivee_id'])
        except ServiceTransportLocal.DoesNotExist:
            pass

    # Calculer le prix total
    prix_total = 0
    if service_depart:
        prix_total += calculer_prix_service('service_depart', 0, int(porte_a_porte['nombre_passagers']))
    if service_principal:
        prix_total += calculer_prix_service('service_principal', 0, int(porte_a_porte['nombre_passagers']))
    if service_arrivee:
        prix_total += calculer_prix_service('service_arrivee', 0, int(porte_a_porte['nombre_passagers']))

    if request.method == 'POST':
        # Récupérer la méthode de paiement
        payment_method = request.POST.get('payment_method', 'card')
        accept_conditions = request.POST.get('accept_conditions') == 'on'
        
        if not accept_conditions:
            messages.error(request, "Vous devez accepter les conditions générales pour continuer.")
            return redirect('confirmer_porte_a_porte')
        
        try:
            # Mettre à jour les détails de la réservation
            reservation.prix = prix_total
            reservation.statut = 'confirmé'
            reservation.save()
            
            # Ajouter des points de fidélité si l'utilisateur est connecté
            if request.user.is_authenticated:
                client = get_or_create_client(request.user)
                from .utils import mettre_a_jour_points_fidelite
                points_ajoutes = mettre_a_jour_points_fidelite(client, prix_total)
                logger.info(f"Points de fidélité ajoutés: {points_ajoutes}")
                messages.info(request, f"Vous avez gagné {points_ajoutes} points de fidélité!")
            
            # Nettoyer la session
            if 'porte_a_porte' in request.session:
                del request.session['porte_a_porte']
            if 'porte_a_porte_id' in request.session:
                del request.session['porte_a_porte_id']
            
            # Message de succès
            messages.success(request, "Votre réservation porte-à-porte a été confirmée avec succès!")
            
            # Rediriger vers l'historique des réservations
            return redirect('historique_reservations')
            
        except Exception as e:
            logger.error(f"Erreur lors de la confirmation de la réservation: {str(e)}")
            messages.error(request, f"Une erreur s'est produite: {str(e)}")
            return redirect('confirmer_porte_a_porte')

    context = {
        'porte_a_porte': porte_a_porte,
        'service_depart': service_depart,
        'service_principal': service_principal,
        'service_arrivee': service_arrivee,
        'prix_total': prix_total
    }

    return render(request, 'Safariyat/confirmer_porte_a_porte.html', context)
def services_additionnels(request):
    """
    Vue pour sélectionner des services additionnels pour une réservation porte-à-porte
    """
    # Récupérer l'ID de réservation depuis la session
    reservation_id = request.session.get('porte_a_porte_id')
    
    if not reservation_id:
        messages.error(request, "Aucune réservation en cours. Veuillez recommencer.")
        return redirect('reserver_porte_a_porte')
    
    try:
        # Récupérer la réservation
        reservation = PorteAPorteReservation.objects.get(id=reservation_id)
        
        if request.method == 'POST':
            # Récupérer les services additionnels sélectionnés
            service_chauffeur = request.POST.get('service_chauffeur') == 'on'
            service_bagages = request.POST.get('service_bagages') == 'on'
            service_guide = request.POST.get('service_guide') == 'on'
            
            # Stocker les services dans la session
            request.session['services_additionnels'] = {
                'service_chauffeur': service_chauffeur,
                'service_bagages': service_bagages,
                'service_guide': service_guide
            }
            
            # Calculer le prix en fonction des services sélectionnés
            prix_base = 200  # Prix de base pour le service porte-à-porte
            
            if service_chauffeur:
                prix_base += 100
            if service_bagages:
                prix_base += 50
            if service_guide:
                prix_base += 150
                
            # Mettre à jour le prix de la réservation
            reservation.prix = prix_base
            reservation.save()
            
            # Rediriger vers la page de confirmation
            return redirect('confirmer_porte_a_porte')
        
        # Préparer le contexte pour le template
        context = {
            'reservation': reservation
        }
        
        return render(request, 'Safariyat/services_additionnels.html', context)
        
    except PorteAPorteReservation.DoesNotExist:
        messages.error(request, "Réservation introuvable.")
        return redirect('reserver_porte_a_porte')
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