# Imports Django pour la gestion des utilisateurs personnalisés
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
# Imports pour les signaux Django (création automatique de profil)
from django.db.models.signals import post_save
from django.dispatch import receiver


class CustomUserManager(BaseUserManager):
    """
    Manager personnalisé pour le modèle CustomUser.
    
    Ce manager remplace le manager par défaut de Django pour permettre
    l'utilisation de l'email comme identifiant principal au lieu du username.
    Il fournit des méthodes pour créer des utilisateurs normaux et des superutilisateurs.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Créer et sauvegarder un utilisateur normal.
        
        Args:
            email (str): Adresse email de l'utilisateur (obligatoire)
            password (str): Mot de passe en clair (sera hashé automatiquement)
            **extra_fields: Champs supplémentaires (first_name, last_name, etc.)
            
        Returns:
            CustomUser: Instance de l'utilisateur créé
            
        Raises:
            ValueError: Si l'email n'est pas fourni
        """
        if not email:
            raise ValueError('L\'adresse email est obligatoire')
        
        # Normalise l'email (convertit le domaine en minuscules)
        email = self.normalize_email(email)
        # Crée une instance du modèle avec les données fournies
        user = self.model(email=email, **extra_fields)
        # Hash le mot de passe avec l'algorithme de Django
        user.set_password(password)
        # Sauvegarde en base de données
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Créer et sauvegarder un superutilisateur.
        
        Un superutilisateur a tous les droits d'administration Django
        et est automatiquement défini comme 'admin' dans notre système.
        
        Args:
            email (str): Adresse email du superutilisateur
            password (str): Mot de passe en clair
            **extra_fields: Champs supplémentaires
            
        Returns:
            CustomUser: Instance du superutilisateur créé
            
        Raises:
            ValueError: Si is_staff ou is_superuser ne sont pas True
        """
        # Définit les valeurs par défaut pour un superutilisateur
        extra_fields.setdefault('is_staff', True)      # Accès à l'admin Django
        extra_fields.setdefault('is_superuser', True)  # Tous les droits
        extra_fields.setdefault('user_type', 'admin')  # Type admin dans notre système
        
        # Validation des permissions requises
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superutilisateur doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superutilisateur doit avoir is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Modèle utilisateur personnalisé utilisant l'email comme identifiant.
    
    Ce modèle étend AbstractBaseUser et PermissionsMixin pour créer un système
    d'authentification basé sur l'email au lieu du username par défaut de Django.
    Il inclut deux types d'utilisateurs : admin et client, avec des permissions
    et des interfaces différentes selon le type.
    
    Hérite de :
        - AbstractBaseUser : Fournit les fonctionnalités de base d'authentification
        - PermissionsMixin : Ajoute le système de permissions et groupes Django
    """
    
    # Définition des types d'utilisateurs disponibles dans le système
    USER_TYPE_CHOICES = [
        ('admin', 'Administrateur'),  # Accès complet à l'administration
        ('client', 'Client'),         # Accès limité aux fonctionnalités client
    ]
    
    # === CHAMPS D'IDENTIFICATION ===
    # Email utilisé comme identifiant unique (remplace username)
    email = models.EmailField(
        'Adresse email',
        unique=True,
        help_text='Adresse email utilisée pour la connexion'
    )
    first_name = models.CharField('Prénom', max_length=30, blank=True)
    last_name = models.CharField('Nom', max_length=30, blank=True)
    
    # Type d'utilisateur déterminant les permissions et l'interface
    user_type = models.CharField(
        'Type d\'utilisateur',
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='client'  # Par défaut, nouvel utilisateur = client
    )
    
    # === CHAMPS DE STATUT ===
    # Détermine si l'utilisateur peut se connecter
    is_active = models.BooleanField(
        'Actif',
        default=True,
        help_text='Indique si cet utilisateur doit être traité comme actif.'
    )
    # Détermine l'accès à l'interface d'administration Django
    is_staff = models.BooleanField(
        'Statut équipe',
        default=False,
        help_text='Indique si l\'utilisateur peut se connecter à l\'admin.'
    )
    
    # === CHAMPS DE DATES ===
    date_joined = models.DateTimeField('Date d\'inscription', default=timezone.now)
    last_login = models.DateTimeField('Dernière connexion', blank=True, null=True)
    
    # === CHAMPS OPTIONNELS ===
    # Champs supplémentaires pour le profil
    phone = models.CharField('Téléphone', max_length=20, blank=True)
    company = models.CharField('Entreprise', max_length=100, blank=True)
    avatar = models.ImageField('Avatar', upload_to='avatars/', blank=True, null=True)
    
    # === CONFIGURATION DU MODÈLE ===
    # Utilise notre manager personnalisé
    objects = CustomUserManager()
    
    # Définit l'email comme champ d'identification principal
    USERNAME_FIELD = 'email'
    # Champs requis lors de la création d'un superutilisateur (en plus de email et password)
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        # Nom de table personnalisé pour éviter les conflits
        db_table = 'auth_user'
    
    def __str__(self):
        """Représentation string de l'utilisateur (utilisée dans l'admin Django)."""
        return self.email
    
    def get_full_name(self):
        """
        Retourne le nom complet de l'utilisateur.
        
        Returns:
            str: Prénom + nom, ou email si les noms ne sont pas renseignés
        """
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name if full_name else self.email
    
    def get_short_name(self):
        """
        Retourne le prénom de l'utilisateur.
        
        Returns:
            str: Prénom ou email si le prénom n'est pas renseigné
        """
        return self.first_name if self.first_name else self.email
    
    # === MÉTHODES UTILITAIRES ===
    @property
    def is_admin(self):
        """
        Vérifie si l'utilisateur est un administrateur.
        
        Returns:
            bool: True si l'utilisateur est de type 'admin' ou superutilisateur
        """
        return self.user_type == 'admin' or self.is_superuser
    
    @property
    def is_client(self):
        """
        Vérifie si l'utilisateur est un client.
        
        Returns:
            bool: True si l'utilisateur est de type 'client'
        """
        return self.user_type == 'client'
    
    def has_group(self, group_name):
        """
        Vérifie si l'utilisateur appartient à un groupe spécifique.
        
        Args:
            group_name (str): Nom du groupe à vérifier
            
        Returns:
            bool: True si l'utilisateur appartient au groupe
        """
        return self.groups.filter(name=group_name).exists()


class UserProfile(models.Model):
    """
    Profil utilisateur avec informations supplémentaires.
    
    Ce modèle étend les informations de base de CustomUser avec des données
    optionnelles comme la bio, localisation, site web, etc. Il utilise une
    relation OneToOne avec CustomUser pour maintenir la séparation des
    préoccupations entre authentification et profil.
    
    Relation :
        - OneToOne avec CustomUser : Un profil par utilisateur
    """
    
    # === RELATION AVEC L'UTILISATEUR ===
    # Relation OneToOne : un profil par utilisateur
    # CASCADE : supprime le profil si l'utilisateur est supprimé
    # related_name : permet d'accéder au profil via user.profile
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # === INFORMATIONS PERSONNELLES ===
    bio = models.TextField('Biographie', max_length=500, blank=True)
    location = models.CharField('Localisation', max_length=30, blank=True)
    birth_date = models.DateField('Date de naissance', null=True, blank=True)
    website = models.URLField('Site web', blank=True)
    
    # === PRÉFÉRENCES DE NOTIFICATION ===
    # Contrôlent comment l'utilisateur souhaite être notifié
    email_notifications = models.BooleanField('Notifications email', default=True)
    sms_notifications = models.BooleanField('Notifications SMS', default=False)
    
    created_at = models.DateTimeField('Créé le', auto_now_add=True)
    updated_at = models.DateTimeField('Modifié le', auto_now=True)
    
    class Meta:
        verbose_name = 'Profil utilisateur'
        verbose_name_plural = 'Profils utilisateurs'
        # Assure qu'un utilisateur ne peut avoir qu'un seul profil
        db_table = 'auth_user_profile'
    
    def __str__(self):
        """Représentation string du profil."""
        return f'Profil de {self.user.email}'
    
    def get_age(self):
        """
        Calcule l'âge de l'utilisateur basé sur sa date de naissance.
        
        Returns:
            int: Âge en années, ou None si la date de naissance n'est pas renseignée
        """
        if self.birth_date:
            from datetime import date
            today = date.today()
            return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None
    
    def has_complete_profile(self):
        """
        Vérifie si le profil est complet (tous les champs optionnels remplis).
        
        Returns:
            bool: True si bio, location, birth_date et website sont renseignés
        """
        return all([
            self.bio.strip(),
            self.location.strip(),
            self.birth_date,
            self.website.strip()
        ])


class PasswordResetToken(models.Model):
    """
    Modèle pour gérer les tokens de réinitialisation de mot de passe.
    
    Chaque token est unique et a une durée de vie limitée (24h par défaut).
    Après utilisation ou expiration, le token devient invalide.
    """
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name='Utilisateur'
    )
    
    token = models.CharField(
        'Token',
        max_length=100,
        unique=True,
        help_text='Token unique pour la réinitialisation'
    )
    
    created_at = models.DateTimeField(
        'Créé le',
        auto_now_add=True
    )
    
    expires_at = models.DateTimeField(
        'Expire le',
        help_text='Date et heure d\'expiration du token'
    )
    
    used = models.BooleanField(
        'Utilisé',
        default=False,
        help_text='Indique si le token a déjà été utilisé'
    )
    
    class Meta:
        verbose_name = 'Token de réinitialisation'
        verbose_name_plural = 'Tokens de réinitialisation'
        db_table = 'auth_password_reset_token'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token pour {self.user.email} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"
    
    def is_valid(self):
        """
        Vérifie si le token est encore valide.
        
        Returns:
            bool: True si le token n'est pas utilisé et n'a pas expiré
        """
        from django.utils import timezone
        return not self.used and self.expires_at > timezone.now()
    
    def mark_as_used(self):
        """
        Marque le token comme utilisé pour empêcher sa réutilisation.
        """
        self.used = True
        self.save()
    
    @classmethod
    def create_token(cls, user):
        """
        Crée un nouveau token de réinitialisation pour un utilisateur.
        
        Args:
            user (CustomUser): L'utilisateur pour qui créer le token
            
        Returns:
            PasswordResetToken: Le token créé
        """
        import secrets
        from django.utils import timezone
        from datetime import timedelta
        
        # Invalider tous les anciens tokens de cet utilisateur
        cls.objects.filter(user=user, used=False).update(used=True)
        
        # Créer un nouveau token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)  # Expire dans 24h
        
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )