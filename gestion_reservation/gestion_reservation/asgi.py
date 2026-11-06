"""
ASGI config for gestion_reservation project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_reservation.settings')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

application = get_asgi_application()
# gestion_reservation/settings.py
# Ajouter ces configurations à votre fichier settings.py existant

# Configuration pour les fichiers média (logos des compagnies, etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
