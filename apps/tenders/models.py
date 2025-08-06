from django.db import models
from django.utils import timezone
from django.conf import settings
import hashlib


class TenderSite(models.Model):
    """
    Modèle représentant les sites web d'appels d'offres.
    """
    name = models.CharField('Nom du site', max_length=100, unique=True)
    url = models.URLField('URL du site')
    description = models.TextField('Description', blank=True)
    is_active = models.BooleanField('Actif', default=True)
    last_scraped = models.DateTimeField('Dernière extraction', null=True, blank=True)
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    updated_at = models.DateTimeField('Modifié le', auto_now=True)

    class Meta:
        verbose_name = 'Site d\'appels d\'offres'
        verbose_name_plural = 'Sites d\'appels d\'offres'
        ordering = ['name']

    def __str__(self):
        return self.name


class Tender(models.Model):
    """
    Modèle représentant un appel d'offres.
    """
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('closed', 'Fermé'),
        ('cancelled', 'Annulé'),
        ('awarded', 'Attribué'),
    ]

    CATEGORY_CHOICES = [
        ('construction', 'Construction'),
        ('services', 'Services'),
        ('supplies', 'Fournitures'),
        ('consulting', 'Conseil'),
        ('maintenance', 'Maintenance'),
        ('other', 'Autre'),
    ]

    # Informations de base
    title = models.CharField('Titre', max_length=500)
    reference = models.CharField('Référence', max_length=100, blank=True)
    description = models.TextField('Description', blank=True)
    category = models.CharField('Catégorie', max_length=20, choices=CATEGORY_CHOICES, default='other')
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Informations sur l'organisme
    organization = models.CharField('Organisme', max_length=300, blank=True)
    contact_person = models.CharField('Personne de contact', max_length=200, blank=True)
    contact_email = models.EmailField('Email de contact', blank=True)
    contact_phone = models.CharField('Téléphone de contact', max_length=20, blank=True)
    
    # Dates importantes
    publication_date = models.DateTimeField('Date de publication', null=True, blank=True)
    deadline_date = models.DateTimeField('Date limite de soumission', null=True, blank=True)
    opening_date = models.DateTimeField('Date d\'ouverture des plis', null=True, blank=True)
    
    # Informations financières
    estimated_value = models.DecimalField('Valeur estimée', max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.CharField('Devise', max_length=3, default='MAD')
    
    # Localisation
    location = models.CharField('Lieu d\'exécution', max_length=300, blank=True)
    region = models.CharField('Région', max_length=100, blank=True)
    
    # Métadonnées de scraping
    site = models.ForeignKey(TenderSite, on_delete=models.CASCADE, related_name='tenders', verbose_name='Site source')
    source_url = models.URLField('URL source', blank=True)
    scraped_at = models.DateTimeField('Extrait le', auto_now_add=True)
    updated_at = models.DateTimeField('Modifié le', auto_now=True)
    
    # Hash pour éviter les doublons
    content_hash = models.CharField('Hash du contenu', max_length=64, unique=True)
    
    class Meta:
        verbose_name = 'Appel d\'offres'
        verbose_name_plural = 'Appels d\'offres'
        ordering = ['-publication_date', '-scraped_at']
        indexes = [
            models.Index(fields=['status', 'deadline_date']),
            models.Index(fields=['site', 'scraped_at']),
            models.Index(fields=['category', 'status']),
        ]

    def __str__(self):
        return f"{self.title[:100]}..."

    @property
    def is_active(self):
        """Vérifie si l'appel d'offres est encore actif."""
        if self.status != 'open':
            return False
        if self.deadline_date and self.deadline_date < timezone.now():
            return False
        return True

    @property
    def deadline(self):
        """Retourne la date limite de soumission."""
        return self.deadline_date
    
    @property
    def days_remaining(self):
        """Calcule le nombre de jours restants avant la date limite."""
        if not self.deadline_date:
            return None
        delta = self.deadline_date - timezone.now()
        return delta.days if delta.days >= 0 else 0

    def save(self, *args, **kwargs):
        """Génère automatiquement le hash du contenu."""
        if not self.content_hash:
            content = f"{self.title}{self.organization}{self.reference}"
            self.content_hash = hashlib.sha256(content.encode()).hexdigest()
        super().save(*args, **kwargs)


class TenderDocument(models.Model):
    """
    Modèle pour les documents associés aux appels d'offres.
    """
    DOCUMENT_TYPES = [
        ('cahier_charges', 'Cahier des charges'),
        ('reglement', 'Règlement de consultation'),
        ('annexe', 'Annexe'),
        ('plan', 'Plan'),
        ('other', 'Autre'),
    ]

    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='documents', verbose_name='Appel d\'offres')
    name = models.CharField('Nom du document', max_length=300)
    document_type = models.CharField('Type de document', max_length=20, choices=DOCUMENT_TYPES, default='other')
    file_url = models.URLField('URL du fichier', blank=True)
    file_path = models.CharField('Chemin du fichier local', max_length=500, blank=True)
    file_size = models.PositiveIntegerField('Taille du fichier (bytes)', null=True, blank=True)
    downloaded = models.BooleanField('Téléchargé', default=False)
    download_date = models.DateTimeField('Date de téléchargement', null=True, blank=True)
    created_at = models.DateTimeField('Créé le', auto_now_add=True)

    class Meta:
        verbose_name = 'Document d\'appel d\'offres'
        verbose_name_plural = 'Documents d\'appels d\'offres'
        ordering = ['document_type', 'name']

    def __str__(self):
        return f"{self.tender.title[:50]} - {self.name}"


class ScrapingLog(models.Model):
    """
    Log des activités de scraping
    """
    STATUS_CHOICES = [
        ('running', 'En cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échec'),
    ]

    site = models.ForeignKey(TenderSite, on_delete=models.CASCADE, related_name='scraping_logs', verbose_name='Site')
    status = models.CharField('Statut', max_length=20, choices=STATUS_CHOICES, default='running')
    started_at = models.DateTimeField('Démarré le', auto_now_add=True)
    completed_at = models.DateTimeField('Terminé le', null=True, blank=True)
    
    # Statistiques
    items_found = models.PositiveIntegerField('Items trouvés', default=0)
    items_new = models.PositiveIntegerField('Nouveaux items', default=0)
    items_updated = models.PositiveIntegerField('Items mis à jour', default=0)
    
    # Erreurs
    error_message = models.TextField('Message d\'erreur', blank=True)
    
    # Métadonnées
    execution_time = models.FloatField('Temps d\'exécution (secondes)', null=True, blank=True)

    class Meta:
        verbose_name = 'Log de scraping'
        verbose_name_plural = 'Logs de scraping'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.site.name} - {self.get_status_display()} - {self.started_at}"
    
    @property
    def duration(self):
        """Retourne la durée d'exécution formatée."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            total_seconds = int(delta.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return None
