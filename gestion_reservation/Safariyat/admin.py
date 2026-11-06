from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from .models import (
    Client, ClientFidelite, Reservation, TaxiReservation,
    CompagnieTransport, Autobus, TrajetAutobus, ModificationReservation,
    ServiceTransportLocal, AutobusReservation, ContactMessage,
    TrainStation, TrainRoute, TrainType, TrainSchedule, TrainReservation,
    Prix, PorteAPorteReservation
)

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'email', 'phone_number')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
    list_filter = ('user__is_active',)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('client', 'travel_date', 'travel_type', 'origin', 'destination', 'amount')
    search_fields = ('client__first_name', 'client__last_name', 'origin', 'destination')
    list_filter = ('travel_type',)

@admin.register(TaxiReservation)
class TaxiReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'depart', 'destination', 'date', 'heure', 'nombre_passagers', 'type_taxi', 'statut', 'ticket_envoye')
    list_filter = ('date', 'type_taxi', 'statut')
    search_fields = ('depart', 'destination')
    date_hierarchy = 'date'

class AutobusInline(admin.TabularInline):
    model = Autobus
    extra = 1
    fields = ('numero_bus', 'type_bus', 'capacite', 'est_climatise', 'wifi_disponible', 'est_actif')

@admin.register(CompagnieTransport)
class CompagnieTransportAdmin(admin.ModelAdmin):
    list_display = ('nom', 'afficher_logo', 'site_web', 'telephone', 'email', 'est_actif', 'nombre_autobus')
    list_filter = ('est_actif',)
    search_fields = ('nom', 'description')
    inlines = [AutobusInline]
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'logo', 'description', 'est_actif')
        }),
        ('Coordonnées', {
            'fields': ('site_web', 'telephone', 'email')
        }),
    )
    
    def afficher_logo(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="50" height="auto" />', obj.logo.url)
        return "-"
    afficher_logo.short_description = "Logo"
    
    def nombre_autobus(self, obj):
        return obj.autobus.count()
    nombre_autobus.short_description = "Nombre d'autobus"

class TrajetAutobusInline(admin.TabularInline):
    model = TrajetAutobus
    extra = 1
    fields = ('ville_depart', 'ville_arrivee', 'heure_depart', 'heure_arrivee', 
              'jours_operation', 'prix_standard', 'places_disponibles', 'est_actif')

@admin.register(Autobus)
class AutobusAdmin(admin.ModelAdmin):
    list_display = ('numero_bus', 'compagnie', 'type_bus', 'capacite', 
                   'est_climatise', 'wifi_disponible', 'prises_electriques', 'est_actif', 'nombre_trajets')
    list_filter = ('compagnie', 'type_bus', 'est_climatise', 'wifi_disponible', 'est_actif')
    search_fields = ('numero_bus', 'compagnie__nom')
    inlines = [TrajetAutobusInline]
    
    def afficher_logo(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="80" height="40" style="object-fit: contain;" />', obj.logo.url)
        return "Pas de logo"
    afficher_logo.short_description = "Logo"
    
    def nombre_trajets(self, obj):
        return obj.trajets.count()
    nombre_trajets.short_description = "Nombre de trajets"

@admin.register(TrajetAutobus)
class TrajetAutobusAdmin(admin.ModelAdmin):
    list_display = ('autobus_info', 'ville_depart', 'ville_arrivee', 'heure_depart', 
                   'heure_arrivee', 'duree', 'prix_standard', 'places_disponibles', 'est_actif')
    list_filter = ('autobus__compagnie', 'ville_depart', 'ville_arrivee', 'est_actif')
    search_fields = ('ville_depart', 'ville_arrivee', 'autobus__numero_bus', 'autobus__compagnie__nom')
    
    def autobus_info(self, obj):
        return f"{obj.autobus.compagnie.nom} - {obj.autobus.numero_bus}"
    autobus_info.short_description = "Autobus"

@admin.register(AutobusReservation)
class AutobusReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'trajet_info', 'date_voyage', 'nombre_passagers', 'prix_total', 'nom_passager', 'statut', 'methode_paiement', 'ticket_envoye')
    list_filter = ('statut', 'methode_paiement', 'date_voyage', 'trajet__autobus__compagnie', 'ticket_envoye')
    search_fields = ('nom_passager', 'email_passager', 'telephone_passager', 'trajet__ville_depart', 'trajet__ville_arrivee')
    date_hierarchy = 'date_voyage'
    actions = ['send_tickets']
    
    def trajet_info(self, obj):
        return f"{obj.trajet.ville_depart} → {obj.trajet.ville_arrivee} ({obj.trajet.autobus.compagnie.nom})"
    trajet_info.short_description = "Trajet"
    
    def send_tickets(self, request, queryset):
        from .pdf_utils import send_ticket_email
        
        success_count = 0
        error_count = 0
        
        for reservation in queryset:
            success, message = send_ticket_email(reservation)
            if success:
                reservation.ticket_envoye = True
                reservation.save(update_fields=['ticket_envoye'])
                success_count += 1
            else:
                error_count += 1
        
        if success_count > 0:
            self.message_user(request, f"{success_count} ticket(s) envoyé(s) avec succès.")
        if error_count > 0:
            self.message_user(request, f"{error_count} erreur(s) lors de l'envoi des tickets.")
    send_tickets.short_description = "Envoyer les tickets aux réservations sélectionnées"

@admin.register(ClientFidelite)
class ClientFideliteAdmin(admin.ModelAdmin):
    list_display = ('client', 'points', 'niveau')
    search_fields = ('client__first_name', 'client__last_name', 'client__email')
    list_filter = ('niveau',)

@admin.register(ModificationReservation)
class ModificationReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation_info', 'type_modification', 'date_demande', 'statut', 'frais', 'remboursement')
    list_filter = ('type_modification', 'statut', 'date_demande')
    search_fields = ('raison',)
    readonly_fields = ('date_demande',)
    actions = ['approuver_demandes', 'refuser_demandes']
    
    def reservation_info(self, obj):
        return f"{obj.get_reservation_type_display()} #{obj.reservation_id}"
    reservation_info.short_description = "Réservation"
    
    def approuver_demandes(self, request, queryset):
        queryset.update(statut='approuvee', date_traitement=timezone.now())
        self.message_user(request, f"{queryset.count()} demande(s) approuvée(s) avec succès.")
    approuver_demandes.short_description = "Approuver les demandes sélectionnées"
    
    def refuser_demandes(self, request, queryset):
        queryset.update(statut='refusee', date_traitement=timezone.now())
        self.message_user(request, f"{queryset.count()} demande(s) refusée(s).")
    refuser_demandes.short_description = "Refuser les demandes sélectionnées"

@admin.register(ServiceTransportLocal)
class ServiceTransportLocalAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_service', 'ville', 'telephone', 'email', 'est_actif')
    list_filter = ('type_service', 'ville', 'est_actif')
    search_fields = ('nom', 'ville', 'adresse')
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'type_service', 'ville', 'adresse', 'est_actif')
        }),
        ('Coordonnées', {
            'fields': ('telephone', 'email', 'site_web')
        }),
        ('Caractéristiques', {
            'fields': ('wifi_disponible', 'climatisation', 'prises_electriques', 'accessibilite_pmr')
        }),
        ('Horaires', {
            'fields': ('horaires_ouverture', 'jours_service')
        }),
        ('API (pour l\'intégration)', {
            'fields': ('api_url', 'api_key', 'api_secret'),
            'classes': ('collapse',)
        }),
    )
    actions = ['activer_services', 'desactiver_services']
    
    def activer_services(self, request, queryset):
        queryset.update(est_actif=True)
        self.message_user(request, f"{queryset.count()} service(s) activé(s) avec succès.")
    activer_services.short_description = "Activer les services sélectionnés"
    
    def desactiver_services(self, request, queryset):
        queryset.update(est_actif=False)
        self.message_user(request, f"{queryset.count()} service(s) désactivé(s).")
    desactiver_services.short_description = "Désactiver les services sélectionnés"

@admin.register(Prix)
class PrixAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_service', 'prix_base', 'prix_par_km', 'prix_par_passager_supp', 'est_actif')
    list_filter = ('type_service', 'est_actif')
    search_fields = ('nom', 'description')
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'type_service', 'description', 'est_actif')
        }),
        ('Tarification', {
            'fields': ('prix_base', 'prix_par_km', 'prix_par_passager_supp')
        }),
    )

@admin.register(TrainStation)
class TrainStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'code')
    search_fields = ('name', 'city')
    list_filter = ('city',)

@admin.register(TrainRoute)
class TrainRouteAdmin(admin.ModelAdmin):
    list_display = ('departure_station', 'arrival_station', 'distance')
    search_fields = ('departure_station__name', 'departure_station__city', 'arrival_station__name', 'arrival_station__city')

@admin.register(TrainType)
class TrainTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

class DaysOfWeekListFilter(admin.SimpleListFilter):
    title = 'jours de service'
    parameter_name = 'day'
    
    def lookups(self, request, model_admin):
        return (
            ('monday', 'Lundi'),
            ('tuesday', 'Mardi'),
            ('wednesday', 'Mercredi'),
            ('thursday', 'Jeudi'),
            ('friday', 'Vendredi'),
            ('saturday', 'Samedi'),
            ('sunday', 'Dimanche'),
            ('weekday', 'Jours de semaine'),
            ('weekend', 'Weekend'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'monday':
            return queryset.filter(days_of_week__startswith='1')
        if self.value() == 'tuesday':
            return queryset.filter(days_of_week__regex=r'^.1')
        if self.value() == 'wednesday':
            return queryset.filter(days_of_week__regex=r'^..1')
        if self.value() == 'thursday':
            return queryset.filter(days_of_week__regex=r'^...1')
        if self.value() == 'friday':
            return queryset.filter(days_of_week__regex=r'^....1')
        if self.value() == 'saturday':
            return queryset.filter(days_of_week__regex=r'^.....1')
        if self.value() == 'sunday':
            return queryset.filter(days_of_week__regex=r'^......1')
        if self.value() == 'weekday':
            return queryset.filter(days_of_week__regex=r'^11111')
        if self.value() == 'weekend':
            return queryset.filter(days_of_week__regex=r'^.....11')
        return queryset

@admin.register(TrainSchedule)
class TrainScheduleAdmin(admin.ModelAdmin):
    list_display = ('route', 'train_type', 'departure_time', 'arrival_time', 'get_duration_display', 'price', 'is_active')
    list_filter = ('is_active', 'train_type', 'route__departure_station__city', 'route__arrival_station__city', DaysOfWeekListFilter)
    search_fields = ('route__departure_station__city', 'route__arrival_station__city')
    readonly_fields = ('duration',)
    fieldsets = (
        (None, {
            'fields': ('route', 'train_type', 'is_active')
        }),
        ('Horaires', {
            'fields': ('departure_time', 'arrival_time', 'duration')
        }),
        ('Tarification', {
            'fields': ('price',)
        }),
        ('Disponibilité', {
            'fields': ('days_of_week',),
            'description': 'Indiquez les jours où ce train circule (1=actif, 0=inactif)'
        }),
    )

@admin.register(TrainReservation)
class TrainReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'depart', 'destination', 'date_voyage', 'nb_passagers', 'classe', 'prix', 'statut')
    list_filter = ('statut', 'classe', 'date_voyage')
    search_fields = ('client__first_name', 'client__last_name', 'depart', 'destination')
    date_hierarchy = 'date_voyage'

@admin.register(PorteAPorteReservation)
class PorteAPorteReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'adresse_depart', 'adresse_destination', 'date', 'nb_passagers', 'statut', 'prix')
    list_filter = ('statut', 'date', 'option_taxi', 'option_bus', 'option_train')
    search_fields = ('adresse_depart', 'adresse_destination', 'client__first_name', 'client__last_name')
    date_hierarchy = 'date'
    readonly_fields = ('date_creation', 'date_modification')
    fieldsets = (
        ('Informations client', {
            'fields': ('client',)
        }),
        ('Détails du trajet', {
            'fields': ('adresse_depart', 'adresse_destination', 'date', 'nb_passagers', 'bagages', 'commentaire')
        }),
        ('Services sélectionnés', {
            'fields': ('service_depart_id', 'service_principal_id', 'service_arrivee_id')
        }),
        ('Options', {
            'fields': ('option_taxi', 'option_bus', 'option_train')
        }),
        ('Paiement et statut', {
            'fields': ('prix', 'statut')
        }),
        ('Suivi', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    def get_services(self, obj):
        """Affiche les services sélectionnés"""
        services = []
        if obj.service_depart_id:
            services.append(f"Départ: {obj.get_service_depart().nom if obj.get_service_depart() else 'N/A'}")
        if obj.service_principal_id:
            services.append(f"Principal: {obj.get_service_principal().nom if obj.get_service_principal() else 'N/A'}")
        if obj.service_arrivee_id:
            services.append(f"Arrivée: {obj.get_service_arrivee().nom if obj.get_service_arrivee() else 'N/A'}")
        return ", ".join(services)
    get_services.short_description = "Services sélectionnés"

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('nom_complet', 'email', 'sujet', 'date_envoi')
    search_fields = ('nom_complet', 'email', 'sujet', 'message')
    list_filter = ('date_envoi',)
    readonly_fields = ('date_envoi',)

class SafariyatAdminSite(admin.AdminSite):
    site_header = "Administration Safariyat"
    site_title = "Portail d'administration Safariyat"
    index_title = "Bienvenue dans le portail d'administration Safariyat"

    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        app_list += [
            {
                'name': 'Fonctionnalités Additionnelles',
                'app_label': 'custom_links',
                'models': [
                    {
                        'name': 'Profils de Fidélité',
                        'admin_url': reverse('admin:Safariyat_clientfidelite_changelist'),
                        'perms': ['Safariyat.view_clientfidelite']
                    },
                    {
                        'name': 'Comparaison des Prix',
                        'admin_url': reverse('admin:Safariyat_comparaisonprix_changelist'),
                        'perms': ['Safariyat.view_comparaisonprix']
                    },
                    {
                        'name': 'Services de Transport Locaux',
                        'admin_url': reverse('admin:Safariyat_servicetransportlocal_changelist'),
                        'perms': ['Safariyat.view_servicetransportlocal']
                    },
                ]
            }
        ]
        return app_list

admin_site = SafariyatAdminSite(name='safariyat_admin')

# Configuration de l'interface d'administration par défaut
admin.site.site_header = "Administration Safariyat"
admin.site.site_title = "Portail d'administration Safariyat"
admin.site.index_title = "Bienvenue dans le portail d'administration Safariyat"