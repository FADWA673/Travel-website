import os
from io import BytesIO
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm

def generate_pdf_ticket(reservation):
    """
    Génère un PDF ticket pour une réservation
    
    Args:
        reservation: Un objet réservation (TaxiReservation, AutobusReservation, etc.)
        
    Returns:
        BytesIO: Un buffer contenant les données PDF
    """
    buffer = BytesIO()
    
    # Créer l'objet PDF avec ReportLab
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Conteneur pour les objets 'Flowable'
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='CenteredTitle',
        parent=styles['Heading1'],
        alignment=1,  # Alignement centré
        spaceAfter=12,
        textColor=colors.blue
    ))
    
    # Ajouter le titre
    elements.append(Paragraph("SAFARIYAT", styles['CenteredTitle']))
    elements.append(Paragraph("Ticket de Réservation", styles['CenteredTitle']))
    elements.append(Spacer(1, 12))
    
    # Récupérer les détails de la réservation
    # Ceci doit être adapté en fonction de votre modèle de réservation
    if hasattr(reservation, 'depart'):
        depart = reservation.depart
    elif hasattr(reservation, 'trajet'):
        depart = reservation.trajet.ville_depart
    else:
        depart = "N/A"
        
    if hasattr(reservation, 'destination'):
        destination = reservation.destination
    elif hasattr(reservation, 'trajet'):
        destination = reservation.trajet.ville_arrivee
    else:
        destination = "N/A"
    
    # Créer le tableau des détails de réservation
    data = [
        ["Numéro de réservation:", f"#{reservation.id}"],
        ["Départ:", depart],
        ["Destination:", destination],
    ]
    
    # Ajouter la date et l'heure
    if hasattr(reservation, 'date'):
        data.append(["Date:", reservation.date.strftime('%d/%m/%Y')])
    elif hasattr(reservation, 'date_voyage'):
        data.append(["Date:", reservation.date_voyage.strftime('%d/%m/%Y')])
    
    if hasattr(reservation, 'heure'):
        data.append(["Heure:", reservation.heure])
    elif hasattr(reservation, 'trajet') and hasattr(reservation.trajet, 'heure_depart'):
        data.append(["Heure:", reservation.trajet.heure_depart.strftime('%H:%M')])
    
    # Ajouter le nombre de passagers et le type de véhicule
    if hasattr(reservation, 'nombre_passagers'):
        data.append(["Nombre de passagers:", str(reservation.nombre_passagers)])
    
    if hasattr(reservation, 'type_taxi'):
        vehicle_type = dict(reservation.TYPE_CHOICES).get(reservation.type_taxi, "N/A")
        data.append(["Type de véhicule:", vehicle_type])
    elif hasattr(reservation, 'trajet') and hasattr(reservation.trajet.autobus, 'type_bus'):
        data.append(["Type de véhicule:", reservation.trajet.autobus.type_bus])
    
    # Ajouter le prix
    if hasattr(reservation, 'prix_total'):
        data.append(["Prix estimé:", f"{reservation.prix_total} DH"])
    
    # Ajouter le statut
    if hasattr(reservation, 'statut'):
        status_map = {
            'en_attente': 'En attente',
            'confirmee': 'Confirmée',
            'en_cours': 'En cours',
            'terminee': 'Terminée',
            'annulee': 'Annulée'
        }
        status = status_map.get(reservation.statut, reservation.statut)
        data.append(["Statut:", status])
    
    # Créer le tableau
    table = Table(data, colWidths=[150, 250])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (1, -1), (1, -1), colors.green),  # Fond vert pour le statut
        ('TEXTCOLOR', (1, -1), (1, -1), colors.white),   # Texte blanc pour le statut
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Ajouter le pied de page
    footer_text = "Merci d'avoir choisi Safariyat pour votre voyage. Pour toute assistance, contactez-nous au +212 522 XX XX XX."
    elements.append(Paragraph(footer_text, styles['Normal']))
    
    # Construire le PDF
    doc.build(elements)
    
    # Récupérer la valeur du buffer BytesIO
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf

def send_ticket_email(reservation, email=None):
    """
    Envoie un ticket PDF par email
    
    Args:
        reservation: Un objet réservation
        email: Adresse email optionnelle. Si non fournie, utilisera l'email de la réservation
        
    Returns:
        tuple: (bool, str) - True si l'email a été envoyé avec succès, False sinon, avec un message
    """
    try:
        # Récupérer l'email de la réservation si non fourni
        if not email:
            if hasattr(reservation, 'email_passager'):
                email = reservation.email_passager
            elif hasattr(reservation, 'client') and hasattr(reservation.client, 'email'):
                email = reservation.client.email
            else:
                return False, "Aucune adresse email trouvée"
        
        # Générer le PDF
        pdf = generate_pdf_ticket(reservation)
        
        # Préparer l'email
        subject = f"Votre ticket de réservation Safariyat #{reservation.id}"
        from_email = settings.DEFAULT_FROM_EMAIL or "noreply@safariyat.com"
        to = [email]
        
        # Créer le corps de l'email à partir du template
        context = {
            'reservation': reservation,
            # Ajouter d'autres variables de contexte nécessaires pour votre template d'email
        }
        
        # Créer les versions texte et HTML
        text_content = render_to_string('Safariyat/emails/ticket_email.txt', context)
        html_content = render_to_string('Safariyat/emails/ticket_email.html', context)
        
        # Créer l'email
        email_message = EmailMultiAlternatives(subject, text_content, from_email, to)
        email_message.attach_alternative(html_content, "text/html")
        
        # Joindre le PDF
        email_message.attach(f'ticket_reservation_{reservation.id}.pdf', pdf, 'application/pdf')
        
        # Envoyer l'email
        email_message.send()
        
        # Mettre à jour le statut d'envoi du ticket dans la réservation
        if hasattr(reservation, 'ticket_envoye'):
            reservation.ticket_envoye = True
            reservation.save(update_fields=['ticket_envoye'])
        
        return True, "Email envoyé avec succès"
    except Exception as e:
        return False, str(e)