from django import forms
from .models import TaxiReservation, ContactMessage, PorteAPorteReservation

from datetime import datetime

class TrainSearchForm(forms.Form):
    depart = forms.CharField(
        label='Gare de départ',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: CASABLANCA'})
    )
    destination = forms.CharField(
        label='Gare d\'arrivée',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: RABAT'})
    )
    date = forms.DateField(
        label='Date de départ',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    heure = forms.TimeField(
        label='Heure de départ',
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'})
    )
    
class ReservationForm(forms.Form):
    ville_depart = forms.CharField(label="De", max_length=100)
    ville_arrivee = forms.CharField(label="A", max_length=100)
    date_depart = forms.DateField(label="Départ", widget=forms.SelectDateWidget())
    date_retour= forms.DateField(label="Retour", widget=forms.SelectDateWidget())
    nombre_places = forms.IntegerField(label="Passagers", min_value=1)
    nom = forms.CharField(label="Nom complet", max_length=100)
    email = forms.EmailField(label="Email")
    telephone = forms.CharField(label="Téléphone", max_length=15)
    
    
class TaxiReservationForm(forms.ModelForm):
    class Meta:
        model = TaxiReservation
        fields = ['depart', 'destination', 'date', 'heure', 'nombre_passagers', 'type_taxi']



# Ajouter ces nouveaux formulaires pour les fonctionnalités demandées

from django import forms
from .models import TaxiReservation, AutobusReservation
import datetime

class AnnulationForm(forms.Form):
    """
    Formulaire pour l'annulation d'une réservation
    """
    raison = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        label="Raison de l'annulation",
        help_text="Veuillez indiquer la raison pour laquelle vous souhaitez annuler cette réservation."
    )

class ModificationForm(forms.Form):
    """
    Formulaire pour la modification d'une réservation
    """
    raison = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        label="Raison de la modification",
        help_text="Veuillez indiquer la raison pour laquelle vous souhaitez modifier cette réservation."
    )
    
    def __init__(self, *args, **kwargs):
        type_reservation = kwargs.pop('type_reservation', None)
        instance = kwargs.pop('instance', None)
        super(ModificationForm, self).__init__(*args, **kwargs)
        
        # Ajouter des champs en fonction du type de réservation
        if type_reservation == 'taxi' and instance:
            # Champs pour la modification d'une réservation de taxi
            self.fields['date'] = forms.DateField(
                widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
                initial=instance.date,
                label="Nouvelle date"
            )
            self.fields['heure'] = forms.TimeField(
                widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
                initial=instance.heure,
                label="Nouvelle heure"
            )
            self.fields['nombre_passagers'] = forms.IntegerField(
                widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8}),
                initial=instance.nombre_passagers,
                label="Nombre de passagers",
                min_value=1,
                max_value=8
            )
        elif type_reservation == 'bus' and instance:
            # Champs pour la modification d'une réservation de bus
            self.fields['date_voyage'] = forms.DateField(
                widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
                initial=instance.date_voyage,
                label="Nouvelle date"
            )
            self.fields['nombre_passagers'] = forms.IntegerField(
                widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
                initial=instance.nombre_passagers,
                label="Nombre de passagers",
                min_value=1,
                max_value=10
            )


from django import forms
from .models import TrainStation
import datetime
# Mettre à jour le formulaire de recherche de trains pour inclure le nombre de passagers
class TrainSearchForm(forms.Form):
    depart = forms.ModelChoiceField(
        queryset=TrainStation.objects.all(),
        label="Ville de départ",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    destination = forms.ModelChoiceField(
        queryset=TrainStation.objects.all(),
        label="Ville d'arrivée",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date = forms.DateField(
        label="Date de départ",
        initial=datetime.date.today,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    heure = forms.TimeField(
        label="Heure de départ",
        initial=datetime.time(8, 0),
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'})
    )
    nombre_passagers = forms.IntegerField(
        label="Nombre de passagers",
        min_value=1,
        max_value=9,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        depart = cleaned_data.get('depart')
        destination = cleaned_data.get('destination')
        
        if depart and destination and depart == destination:
            raise forms.ValidationError("La ville de départ et la ville d'arrivée ne peuvent pas être identiques.")
        
        return cleaned_data

class PorteAPorteForm(forms.ModelForm):
    class Meta:
        model = PorteAPorteReservation
        fields = ['adresse_depart', 'adresse_destination', 'date', 'nb_passagers', 'commentaire']
        widgets = {
            'commentaire': forms.Textarea(attrs={'rows': 4}),
        }

class ContactForm(forms.ModelForm):
    """
    Form for the contact page
    """
    class Meta:
        model = ContactMessage
        fields = ['nom_complet', 'email', 'sujet', 'message']
        widgets = {
            'nom_complet': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre nom complet'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Votre adresse email'}),
            'sujet': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sujet de votre message'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Votre message'})
        }