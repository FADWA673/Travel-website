# Safariyat - Plateforme de Réservation de Transport

Application web Django pour la réservation de transports au Maroc (taxi, bus, train) avec système de fidélité, génération de tickets PDF et interface d'administration complète.

## Fonctionnalités

- **Réservation Taxi** : réservation de taxis (standard, premium, familial) avec calcul de prix selon la distance et le nombre de passagers
- **Réservation Bus** : recherche et réservation de trajets en autobus avec comparaison des compagnies de transport
- **Réservation Train** : recherche de trajets en train (ONCF) avec sélection des horaires et des classes
- **Service Porte-à-Porte** : combinaison de plusieurs modes de transport pour un trajet complet de porte à porte
- **Système de Fidélité** : programme de fidélité avec points et niveaux (Bronze, Argent, Or, Platine) offrant des réductions
- **Tickets PDF** : génération de tickets de réservation au format PDF envoyés par email
- **Annulation et Modification** : système de gestion des annulations avec politiques de remboursement (flexible, modérée, stricte)
- **Interface Admin** : gestion des compagnies, autobus, horaires de train, prix et services de transport local
- **Authentification** : inscription, connexion et gestion de profil utilisateur

## Technologies

- Python 3.10+
- Django 5.0
- MySQL / MariaDB 10.4+
- ReportLab (génération PDF)
- Pillow (gestion des images)

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/FADWA673/travel-website.git
cd travel-website-main
```

### 2. Créer un environnement virtuel

```bash
cd gestion_reservation
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r ../requirements.txt
```

### 4. Configurer la base de données

Créer une base de données MySQL/MariaDB :

```sql
CREATE DATABASE gestion_stock;
```

Vérifier la configuration dans `gestion_reservation/settings.py` :

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'gestion_stock',
        'USER': 'root',
        'PASSWORD': '',          # Votre mot de passe MySQL
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 5. Appliquer les migrations

```bash
python manage.py migrate
```

### 6. Créer un superutilisateur

```bash
python manage.py createsuperuser
```

### 7. Lancer le serveur

```bash
python manage.py runserver
```

Le site est accessible sur :

- Application : http://127.0.0.1:8000/safariyat/
- Administration : http://127.0.0.1:8000/admin/

## Structure du projet

```
travel-website-main/
├── gestion_reservation/          # Projet Django
│   ├── gestion_reservation/       # Configuration du projet (settings, urls, wsgi)
│   ├── Safariyat/                 # Application principale
│   │   ├── models.py              # Modèles (Client, Reservation, Train, Bus, Taxi...)
│   │   ├── views.py               # Vues et logique métier
│   │   ├── forms.py               # Formulaires
│   │   ├── admin.py               # Configuration de l'interface admin
│   │   ├── pdf_utils.py           # Génération de tickets PDF
│   │   ├── urls.py                # Routes de l'application
│   │   ├── templates/             # Templates HTML
│   │   ├── static/                # Fichiers statiques (CSS, images)
│   │   └── migrations/            # Migrations de base de données
│   ├── manage.py
│   └── city_data.json             # Données des villes
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## Déploiement avec Docker

Un fichier `docker-compose.yml` est fourni pour un déploiement conteneurisé :

```bash
docker-compose up --build
```

## Contribution

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines de contribution.

## Licence

Ce projet est développé dans le cadre d'un Projet de Fin d'Année (PFA).
