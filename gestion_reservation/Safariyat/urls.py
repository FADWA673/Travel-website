from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Autres URLs existantes...
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('choix-transport/', views.choix_transport, name='choix_transport'),
    path('about/', views.about, name='about'),
    path('reservation/', views.reservation_view, name='reservation'),
    path('signup/', views.signup, name='signup'),
    path('password_reset/', views.password_reset, name='password_reset'),
    path('compagnies/', views.compagnies, name='compagnies_autobus'),
    path('reservation_bus/', views.reservation_bus, name='reservation_bus'),
    path('reserver-taxi/', views.reserver_taxi, name='reserver_taxi'),
    path('', views.accueil, name='accueil'),
    path('reservation_train/', views.reservation_train, name='reservation_train'),
    path('reservation/confirmation/', views.reservation_confirmation, name='reservation_confirmation'),
    path('paiement/', views.paiement, name='paiement'),
    path('confirmation-finale/', views.confirmation_finale, name='confirmation_finale'),
    # Autres URLs...
    path('confirmation-reservation/<int:reservation_id>/', views.confirmation_finale, name='confirmation_reservation_with_id'),
    path('send_receipt/', views.send_receipt, name='send_receipt'),
   
    path('create-client-profile/', views.create_client_profile, name='create_client_profile'),
    path('historique/', views.historique_reservations, name='historique'),
    path('historique-reservations/', views.historique_reservations, name='historique_reservations'),
    path('profil-fidelite/', views.profil_fidelite, name='profil_fidelite'),
    path('train-search/', views.train_search, name='train_search'),
    path('reservation-train/', views.reservation_train, name='reservation_train'),
    path('train-results/', views.train_results, name='train_results'),
    path('train-seats-payment/<int:train_id>/', views.train_seats_payment, name='train_seats_payment'),
    path('train-confirmation/', views.train_confirmation, name='train_confirmation'),
   
    path('disponibilites/', views.disponibilites, name='disponibilites'),
    # Ajouter cette URL pour la confirmation de réservation de taxi
    path('taxi-confirmation/', views.taxi_confirmation, name='taxi_confirmation'),
    path('taxi-confirmation-page/', views.taxi_confirmation_page, name='taxi_confirmation_page'),
    path('send-ticket/<int:reservation_id>/', views.send_reservation_ticket, name='send_reservation_ticket'),
    path('download-ticket/<str:reservation_type>/<int:reservation_id>/', views.download_ticket, name='download_ticket'),
    path('admin/historique/', views.admin_historique_reservations, name='admin_historique'),

    # Système de fidélité
    path('fidelite/', views.profil_fidelite, name='profil_fidelite'),
    
    # Annulation et modification
    path('annuler/<str:type_reservation>/<int:reservation_id>/', views.annuler_reservation, name='annuler_reservation'),
    path('modifier/<str:type_reservation>/<int:reservation_id>/', views.modifier_reservation, name='modifier_reservation'),
    
    
    # Intégration avec les services de transport locaux
    path('services-locaux/', views.services_locaux, name='services_locaux'),
    path('reserver-porte-a-porte/', views.reserver_porte_a_porte, name='reserver_porte_a_porte'),
    path('selectionner-services/', views.selectionner_services, name='selectionner_services'),
    path('confirmer-porte-a-porte/', views.confirmer_porte_a_porte, name='confirmer_porte_a_porte'),  path('debug-train-reservations/', views.debug_train_reservations, name='debug_train_reservations'),
    path('services-additionnels/', views.services_additionnels, name='services_additionnels'),
]


# Ajout de la configuration pour servir les fichiers média en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
