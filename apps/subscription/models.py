# === IMPORTS ===
from django.db import models
# settings : Accès aux paramètres Django (AUTH_USER_MODEL)
from django.conf import settings
# timezone : Gestion des dates/heures avec timezone
from django.utils import timezone
# timedelta : Calculs de durées
from datetime import timedelta


class Plan(models.Model):
    """
    Modèle représentant les différents plans d'abonnement disponibles.
    
    Ce modèle définit :
    - Les types de plans (gratuit, basique, premium, entreprise)
    - La tarification et les cycles de facturation
    - Les limites et fonctionnalités de chaque plan
    - Les métadonnées d'affichage et de gestion
    
    Utilisation :
        - Création de plans par les administrateurs
        - Sélection de plans par les utilisateurs
        - Gestion des fonctionnalités selon le plan
    """
    
    # === CHOIX DISPONIBLES ===
    # Types de plans avec niveaux croissants de fonctionnalités
    PLAN_TYPE_CHOICES = [
        ('free', 'Gratuit'),        # Plan de base sans coût
        ('basic', 'Basique'),       # Plan d'entrée payant
        ('premium', 'Premium'),     # Plan avancé
        ('enterprise', 'Entreprise'), # Plan pour grandes organisations
    ]
    
    # Cycles de facturation disponibles
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Mensuel'),     # Facturation mensuelle
        ('yearly', 'Annuel'),       # Facturation annuelle (souvent avec réduction)
        ('lifetime', 'À vie'),      # Paiement unique
    ]
    
    # === INFORMATIONS DE BASE ===
    # Nom affiché du plan (ex: "Plan Premium")
    name = models.CharField('Nom du plan', max_length=100)
    # Slug pour les URLs (ex: "premium")
    slug = models.SlugField('Slug', unique=True)
    # Description détaillée du plan
    description = models.TextField('Description', blank=True)
    # Type de plan déterminant le niveau de service
    plan_type = models.CharField(
        'Type de plan',
        max_length=20,
        choices=PLAN_TYPE_CHOICES,
        default='free'  # Par défaut, plan gratuit
    )
    
    # === TARIFICATION ===
    # Prix du plan (0.00 pour les plans gratuits)
    price = models.DecimalField(
        'Prix',
        max_digits=10,  # Permet des prix jusqu'à 99 999 999.99
        decimal_places=2,  # Précision au centime
        default=0.00
    )
    # Fréquence de facturation
    billing_cycle = models.CharField(
        'Cycle de facturation',
        max_length=20,
        choices=BILLING_CYCLE_CHOICES,
        default='monthly'  # Par défaut, facturation mensuelle
    )
    
    # === LIMITES ET QUOTAS ===
    # Nombre d'utilisateurs autorisés (0 = illimité)
    max_users = models.PositiveIntegerField(
        'Nombre maximum d\'utilisateurs',
        default=1,
        help_text='0 = illimité'
    )
    # Nombre de projets autorisés (0 = illimité)
    max_projects = models.PositiveIntegerField(
        'Nombre maximum de projets',
        default=1,
        help_text='0 = illimité'
    )
    # Espace de stockage alloué en GB (0 = illimité)
    storage_limit_gb = models.PositiveIntegerField(
        'Limite de stockage (GB)',
        default=1,
        help_text='0 = illimité'
    )
    
    # === FONCTIONNALITÉS PREMIUM ===
    # Accès aux API pour intégrations
    has_api_access = models.BooleanField('Accès API', default=False)
    # Support client prioritaire
    has_priority_support = models.BooleanField('Support prioritaire', default=False)
    # Outils d'analyse et statistiques avancées
    has_analytics = models.BooleanField('Analyses avancées', default=False)
    # Personnalisation de l'interface (logo, couleurs)
    has_custom_branding = models.BooleanField('Personnalisation de marque', default=False)
    
    # === MÉTADONNÉES DE GESTION ===
    # Détermine si le plan est disponible à la souscription
    is_active = models.BooleanField('Actif', default=True)
    # Plan mis en avant sur la page de tarification
    is_featured = models.BooleanField('Mis en avant', default=False)
    # Ordre d'affichage des plans (0 = premier)
    sort_order = models.PositiveIntegerField('Ordre d\'affichage', default=0)
    
    # === HORODATAGE ===
    # === HORODATAGE ===
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    updated_at = models.DateTimeField('Modifié le', auto_now=True)
    
    class Meta:
        verbose_name = 'Plan d\'abonnement'
        verbose_name_plural = 'Plans d\'abonnement'
        # Tri par ordre d'affichage puis par prix croissant
        ordering = ['sort_order', 'price']
    
    # === MÉTHODES D'AFFICHAGE ===
    def __str__(self):
        """
        Représentation textuelle du plan.
        
        Returns:
            str: Nom du plan avec son prix formaté
        """
        return f'{self.name} - {self.get_price_display()}'
    
    def get_price_display(self):
        """
        Formate le prix du plan avec la devise et le cycle de facturation.
        
        Returns:
            str: Prix formaté (ex: "29.99€/mois", "Gratuit")
        """
        if self.price == 0:
            return 'Gratuit'
        
        # Mapping des cycles de facturation vers leur suffixe d'affichage
        cycle_text = {
            'monthly': '/mois',
            'yearly': '/an',
            'lifetime': ' (à vie)'
        }.get(self.billing_cycle, '')
        
        return f'{self.price}€{cycle_text}'
    
    def get_features_list(self):
        """
        Génère la liste des fonctionnalités et limites du plan.
        
        Returns:
            list: Liste des fonctionnalités formatées pour l'affichage
        """
        features = []
        
        # Gestion des utilisateurs
        if self.max_users == 0:
            features.append('Utilisateurs illimités')
        else:
            features.append(f'{self.max_users} utilisateur(s)')
        
        # Gestion des projets
        if self.max_projects == 0:
            features.append('Projets illimités')
        else:
            features.append(f'{self.max_projects} projet(s)')
        
        if self.storage_limit_gb == 0:
            features.append('Stockage illimité')
        else:
            features.append(f'{self.storage_limit_gb} GB de stockage')
        
        if self.has_api_access:
            features.append('Accès API')
        
        if self.has_priority_support:
            features.append('Support prioritaire')
        
        if self.has_analytics:
            features.append('Analyses avancées')
        
        if self.has_custom_branding:
            features.append('Personnalisation de marque')
        
        return features


class Subscription(models.Model):
    """
    Modèle représentant l'abonnement d'un utilisateur à un plan.
    
    Ce modèle gère :
    - La relation utilisateur-plan
    - Le statut et les dates de l'abonnement
    - La facturation et les paiements
    - Les périodes d'essai
    - L'historique des changements
    
    Utilisation :
        - Création lors de la souscription à un plan
        - Suivi du statut et des renouvellements
        - Gestion des upgrades/downgrades
        - Contrôle d'accès aux fonctionnalités
    """
    
    # === STATUTS DISPONIBLES ===
    STATUS_CHOICES = [
        ('active', 'Actif'),        # Abonnement en cours et valide
        ('inactive', 'Inactif'),    # Abonnement suspendu temporairement
        ('cancelled', 'Annulé'),    # Abonnement annulé par l'utilisateur
        ('expired', 'Expiré'),      # Abonnement arrivé à expiration
        ('pending', 'En attente'),  # Abonnement en attente de paiement
    ]
    
    # === RELATIONS ===
    # Utilisateur propriétaire de l'abonnement
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,  # Suppression en cascade si utilisateur supprimé
        related_name='subscriptions',  # Accès via user.subscriptions.all()
        verbose_name='Utilisateur'
    )
    # Plan souscrit
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,  # Suppression en cascade si plan supprimé
        related_name='subscriptions',  # Accès via plan.subscriptions.all()
        verbose_name='Plan'
    )
    
    # === STATUT ET ÉTAT ===
    # Statut actuel de l'abonnement
    status = models.CharField(
        'Statut',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'  # Par défaut, en attente de validation
    )
    
    # === DATES ET PÉRIODES ===
    # Date de début de l'abonnement
    start_date = models.DateTimeField('Date de début', default=timezone.now)
    # Date de fin de l'abonnement (null = illimité)
    end_date = models.DateTimeField('Date de fin', null=True, blank=True)
    # Date de la prochaine facturation
    next_billing_date = models.DateTimeField('Prochaine facturation', null=True, blank=True)
    
    # === INFORMATIONS FINANCIÈRES ===
    # Montant total payé pour cet abonnement
    amount_paid = models.DecimalField(
        'Montant payé',
        max_digits=10,  # Jusqu'à 99 999 999.99
        decimal_places=2,  # Précision au centime
        default=0.00
    )
    
    # === PÉRIODE D'ESSAI ===
    # Indique si l'abonnement est en période d'essai
    is_trial = models.BooleanField('Période d\'essai', default=False)
    # Date de fin de la période d'essai
    trial_end_date = models.DateTimeField('Fin de l\'essai', null=True, blank=True)
    
    # === INFORMATIONS DE TRANSACTION ===
    # Méthode utilisée pour le paiement
    payment_method = models.CharField(
        'Méthode de paiement',
        max_length=50,
        blank=True,
        help_text='Ex: Carte bancaire, PayPal, etc.'
    )
    # Identifiant unique de la transaction de paiement
    transaction_id = models.CharField(
        'ID de transaction',
        max_length=100,
        blank=True
    )
    
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    updated_at = models.DateTimeField('Modifié le', auto_now=True)
    
    class Meta:
        verbose_name = 'Abonnement'
        verbose_name_plural = 'Abonnements'
        ordering = ['-created_at']  # Tri par date de création décroissante
        # Un utilisateur ne peut avoir qu'un seul abonnement actif par plan
        unique_together = ['user', 'plan', 'status']
    
    # === MÉTHODES D'AFFICHAGE ===
    def __str__(self):
        """
        Représentation textuelle de l'abonnement.
        
        Returns:
            str: Email utilisateur, nom du plan et statut
        """
        return f'{self.user.email} - {self.plan.name} ({self.status})'
    
    # === MÉTHODES DE GESTION ===
    def save(self, *args, **kwargs):
        """
        Sauvegarde l'abonnement avec calcul automatique des dates.
        
        Calcule automatiquement :
        - La date de fin selon le cycle de facturation
        - La date de prochaine facturation
        
        Args:
            *args: Arguments positionnels
            **kwargs: Arguments nommés
        """
        # Calcul automatique des dates pour les plans non-lifetime
        if not self.end_date and self.plan.billing_cycle != 'lifetime':
            if self.plan.billing_cycle == 'monthly':
                self.end_date = self.start_date + timedelta(days=30)
                self.next_billing_date = self.end_date
            elif self.plan.billing_cycle == 'yearly':
                self.end_date = self.start_date + timedelta(days=365)
                self.next_billing_date = self.end_date
        
        super().save(*args, **kwargs)
    
    # === PROPRIÉTÉS DE STATUT ===
    @property
    def is_active(self):
        """
        Vérifie si l'abonnement est actuellement actif.
        
        Un abonnement est actif si :
        - Son statut est 'active'
        - Il n'a pas expiré (si une date de fin est définie)
        
        Returns:
            bool: True si l'abonnement est actif, False sinon
        """
        if self.status != 'active':
            return False
        
        # Vérification de l'expiration
        if self.end_date and timezone.now() > self.end_date:
            return False
        
        return True
    
    @property
    def is_expired(self):
        """
        Vérifie si l'abonnement a expiré.
        
        Returns:
            bool: True si l'abonnement a expiré, False sinon
                 (False aussi pour les abonnements sans date de fin)
        """
        if not self.end_date:
            return False  # Pas de date de fin = pas d'expiration
        return timezone.now() > self.end_date
    
    @property
    def days_remaining(self):
        """
        Calcule le nombre de jours restants avant expiration.
        
        Returns:
            int|None: Nombre de jours restants (minimum 0)
                     None si pas de date de fin définie
        """
        if not self.end_date:
            return None  # Abonnement sans limite de temps
        
        remaining = self.end_date - timezone.now()
        return max(0, remaining.days)  # Jamais négatif
    
    # === ACTIONS SUR L'ABONNEMENT ===
    def cancel(self):
        """
        Annule l'abonnement en changeant son statut.
        
        L'abonnement reste accessible jusqu'à sa date de fin
        mais ne sera pas renouvelé automatiquement.
        """
        self.status = 'cancelled'
        self.save()
    
    def renew(self):
        """
        Renouvelle l'abonnement pour une nouvelle période.
        
        Étend les dates de fin et de prochaine facturation
        selon le cycle de facturation du plan.
        """
        if self.plan.billing_cycle == 'monthly':
            self.end_date = timezone.now() + timedelta(days=30)
        elif self.plan.billing_cycle == 'yearly':
            self.end_date = timezone.now() + timedelta(days=365)
        
        self.status = 'active'
        self.next_billing_date = self.end_date
        self.save()


class SubscriptionHistory(models.Model):
    """
    Modèle pour tracer l'historique des changements d'abonnement.
    
    Ce modèle enregistre :
    - Toutes les actions effectuées sur un abonnement
    - Les changements de plan (upgrade/downgrade)
    - Les renouvellements et annulations
    - Des notes explicatives pour chaque action
    
    Utilisation :
        - Audit trail des modifications
        - Suivi des changements de plan
        - Analyse des comportements utilisateur
        - Support client et facturation
    """
    
    # === ACTIONS POSSIBLES ===
    ACTION_CHOICES = [
        ('created', 'Créé'),           # Création initiale de l'abonnement
        ('upgraded', 'Mis à niveau'),  # Passage à un plan supérieur
        ('downgraded', 'Rétrogradé'),  # Passage à un plan inférieur
        ('renewed', 'Renouvelé'),      # Renouvellement de l'abonnement
        ('cancelled', 'Annulé'),       # Annulation par l'utilisateur
        ('expired', 'Expiré'),         # Expiration automatique
    ]
    
    # === RELATIONS ET DONNÉES ===
    # Abonnement concerné par cette entrée d'historique
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,  # Suppression en cascade avec l'abonnement
        related_name='history',    # Accès via subscription.history.all()
        verbose_name='Abonnement'
    )
    # Type d'action effectuée
    action = models.CharField(
        'Action',
        max_length=20,
        choices=ACTION_CHOICES
    )
    # Plan précédent (pour les changements de plan)
    old_plan = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,  # Garde l'historique même si plan supprimé
        null=True,
        blank=True,
        related_name='old_subscriptions',
        verbose_name='Ancien plan'
    )
    # Nouveau plan (pour les changements de plan)
    new_plan = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,  # Garde l'historique même si plan supprimé
        null=True,
        blank=True,
        related_name='new_subscriptions',
        verbose_name='Nouveau plan'
    )
    # Notes explicatives sur l'action
    notes = models.TextField('Notes', blank=True)
    # Date et heure de l'action
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Historique d\'abonnement'
        verbose_name_plural = 'Historiques d\'abonnement'
        ordering = ['-created_at']  # Tri par date décroissante (plus récent en premier)
    
    # === MÉTHODES D'AFFICHAGE ===
    def __str__(self):
        """
        Représentation textuelle de l'entrée d'historique.
        
        Returns:
            str: Email utilisateur, action et date formatée
        """
        return f'{self.subscription.user.email} - {self.action} - {self.created_at.strftime("%d/%m/%Y")}'