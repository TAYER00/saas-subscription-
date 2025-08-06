# ============================================================================
# COMMANDE DE GESTION DJANGO : INITIALISATION DES RÔLES ET PERMISSIONS
# ============================================================================
# Ce fichier définit une commande Django personnalisée pour initialiser
# le système de permissions et de rôles de l'application SaaS.
# 
# Usage: python manage.py init_roles [--reset]

# Imports Django pour la gestion des commandes
from django.core.management.base import BaseCommand  # Classe de base pour les commandes Django
from django.contrib.auth.models import Group, Permission  # Modèles pour groupes et permissions
from django.contrib.contenttypes.models import ContentType  # Pour les permissions personnalisées

# Import du modèle utilisateur personnalisé
from apps.auth.models import CustomUser


class Command(BaseCommand):
    """
    Commande Django pour initialiser les groupes et permissions du système SaaS.
    
    Cette commande :
    - Crée les groupes 'admin' et 'client'
    - Assigne les permissions appropriées à chaque groupe
    - Crée des utilisateurs de test si nécessaire
    - Affiche un résumé de la configuration
    
    Utilisation :
        python manage.py init_roles          # Initialisation normale
        python manage.py init_roles --reset  # Réinitialisation complète
    """
    help = 'Initialise les groupes et permissions pour le système SaaS'
    
    def add_arguments(self, parser):
        """
        Définit les arguments de ligne de commande acceptés.
        
        Args:
            parser: ArgumentParser de Django pour définir les options
        """
        parser.add_argument(
            '--reset',
            action='store_true',  # Option booléenne (présente ou absente)
            help='Supprime et recrée tous les groupes existants',
        )
    
    def handle(self, *args, **options):
        """
        Méthode principale qui exécute la logique de la commande.
        
        Cette méthode :
        1. Gère l'option --reset pour supprimer les groupes existants
        2. Crée les groupes 'admin' et 'client'
        3. Configure les permissions pour chaque groupe
        4. Crée des utilisateurs de test
        5. Affiche un résumé de la configuration
        
        Args:
            *args: Arguments positionnels (non utilisés)
            **options: Options de ligne de commande (contient 'reset')
        """
        
        # ========================================
        # ÉTAPE 1: GESTION DE L'OPTION --reset
        # ========================================
        # Si l'option --reset est présente, supprime les groupes existants
        # pour permettre une réinitialisation complète
        if options['reset']:
            self.stdout.write(
                self.style.WARNING('Suppression des groupes existants...')
            )
            # Supprime uniquement les groupes de notre système
            Group.objects.filter(name__in=['admin', 'client']).delete()
        
        # ========================================
        # ÉTAPE 2: CRÉATION DES GROUPES
        # ========================================
        # get_or_create() retourne un tuple (objet, created)
        # - objet: l'instance du groupe (existante ou nouvellement créée)
        # - created: booléen indiquant si l'objet a été créé (True) ou existait déjà (False)
        
        admin_group, admin_created = Group.objects.get_or_create(name='admin')
        client_group, client_created = Group.objects.get_or_create(name='client')
        
        # Affichage des messages de confirmation pour le groupe admin
        if admin_created:
            self.stdout.write(
                self.style.SUCCESS('Groupe "admin" créé avec succès')
            )
        else:
            self.stdout.write('Groupe "admin" existe déjà')
        
        # Affichage des messages de confirmation pour le groupe client
        if client_created:
            self.stdout.write(
                self.style.SUCCESS('Groupe "client" créé avec succès')
            )
        else:
            self.stdout.write('Groupe "client" existe déjà')
        
        # ========================================
        # ÉTAPE 3: CONFIGURATION DES PERMISSIONS ADMIN
        # ========================================
        # Les administrateurs ont TOUTES les permissions du système
        # Permission.objects.all() récupère toutes les permissions Django
        # (modèles, vues, actions CRUD, etc.)
        admin_permissions = Permission.objects.all()
        
        # .set() remplace toutes les permissions existantes du groupe
        # par la nouvelle liste (équivalent à clear() puis add())
        admin_group.permissions.set(admin_permissions)
        
        self.stdout.write(
            f'Toutes les permissions ({admin_permissions.count()}) '
            'assignées au groupe "admin"'
        )
        
        # ========================================
        # ÉTAPE 4: CONFIGURATION DES PERMISSIONS CLIENT
        # ========================================
        # Les clients ont des permissions limitées et spécifiques
        # Utilisation de filter() avec codename__in pour sélectionner
        # uniquement les permissions nécessaires aux clients
        
        client_permissions = Permission.objects.filter(
            codename__in=[
                # ---- PERMISSIONS DE PROFIL UTILISATEUR ----
                # Ces permissions permettent aux clients de gérer leur propre compte
                'view_customuser',    # Voir son propre profil utilisateur
                'change_customuser',  # Modifier ses informations personnelles
                'view_userprofile',   # Consulter son profil étendu
                'change_userprofile', # Modifier son profil étendu (bio, avatar, etc.)
                
                # ---- PERMISSIONS D'ABONNEMENT ----
                # Ces permissions gèrent l'interaction avec le système d'abonnement
                'view_subscription',   # Consulter les détails de son abonnement
                'add_subscription',    # Créer un nouvel abonnement (s'abonner)
                'change_subscription', # Modifier son abonnement (upgrade/downgrade)
                
                # ---- PERMISSIONS DE CONSULTATION DES PLANS ----
                # Permission en lecture seule pour voir les offres disponibles
                'view_plan',  # Consulter les plans d'abonnement disponibles
            ]
        )
        
        # Application des permissions sélectionnées au groupe client
        # .set() remplace toutes les permissions existantes
        client_group.permissions.set(client_permissions)
        
        # Affichage du nombre de permissions assignées
        self.stdout.write(
            f'{client_permissions.count()} permissions '
            'assignées au groupe "client"'
        )
        
        # ========================================
        # ÉTAPE 5: CRÉATION DU SUPERUTILISATEUR
        # ========================================
        # Vérifie s'il existe déjà un superutilisateur dans le système
        # Si aucun n'existe, en crée un pour permettre l'accès initial à l'admin
        
        if not CustomUser.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING(
                    'Aucun superutilisateur trouvé. '
                    'Création d\'un compte administrateur par défaut...'
                )
            )
            
            # create_superuser() est une méthode spéciale qui :
            # - Définit is_staff=True et is_superuser=True automatiquement
            # - Hash le mot de passe
            # - Valide les champs requis
            admin_user = CustomUser.objects.create_superuser(
                email='admin@saas.com',      # Email de connexion
                password='admin123',         # Mot de passe par défaut (À CHANGER !)
                first_name='Admin',          # Prénom
                last_name='System',          # Nom de famille
                user_type='admin'            # Type d'utilisateur personnalisé
            )
            
            # Ajout du superutilisateur au groupe admin
            # Cela lui donne accès aux permissions définies pour ce groupe
            admin_user.groups.add(admin_group)
            
            # Affichage des informations de connexion avec avertissement sécurité
            self.stdout.write(
                self.style.SUCCESS(
                    'Superutilisateur créé:\n'
                    'Email: admin@saas.com\n'
                    'Mot de passe: admin123\n'
                    'IMPORTANT: Changez ce mot de passe en production!'
                )
            )
        
        # ========================================
        # ÉTAPE 6: CRÉATION D'UN UTILISATEUR CLIENT DE TEST
        # ========================================
        # Crée un utilisateur client pour tester les fonctionnalités
        # Vérifie d'abord si cet utilisateur n'existe pas déjà
        
        if not CustomUser.objects.filter(email='client@test.com').exists():
            # create_user() est la méthode standard qui :
            # - Hash le mot de passe
            # - Définit is_staff=False et is_superuser=False
            # - Valide les champs requis
            client_user = CustomUser.objects.create_user(
                email='client@test.com',     # Email de connexion unique
                password='client123',        # Mot de passe de test
                first_name='Client',         # Prénom
                last_name='Test',            # Nom de famille
                user_type='client'           # Type d'utilisateur (client standard)
            )
            
            # Ajout de l'utilisateur au groupe client
            # Cela lui donne les permissions limitées définies pour les clients
            client_user.groups.add(client_group)
            
            # Confirmation de création avec informations de connexion
            self.stdout.write(
                self.style.SUCCESS(
                    'Utilisateur client de test créé:\n'
                    'Email: client@test.com\n'
                    'Mot de passe: client123'
                )
            )
        
        # ========================================
        # ÉTAPE 7: AFFICHAGE DU RÉSUMÉ FINAL
        # ========================================
        # Cette section affiche un résumé complet de l'initialisation
        # avec des statistiques sur les groupes, permissions et utilisateurs
        
        # En-tête du résumé avec séparateur visuel
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('RÉSUMÉ DE L\'INITIALISATION'))
        self.stdout.write('='*50)
        
        # Statistiques générales du système
        # Compte le nombre total d'objets créés/existants
        self.stdout.write(f'Groupes créés: {Group.objects.count()}')
        self.stdout.write(f'Permissions totales: {Permission.objects.count()}')
        self.stdout.write(f'Utilisateurs admin: {CustomUser.objects.filter(user_type="admin").count()}')
        self.stdout.write(f'Utilisateurs client: {CustomUser.objects.filter(user_type="client").count()}')
        
        # Message de confirmation finale
        self.stdout.write('\nGroupes et permissions configurés avec succès!')
        
        # ========================================
        # ÉTAPE 8: DÉTAIL DES PERMISSIONS PAR GROUPE
        # ========================================
        # Affiche un aperçu des permissions assignées à chaque groupe
        # Utile pour vérifier la configuration
        
        self.stdout.write('\n' + '-'*30)
        self.stdout.write('PERMISSIONS PAR GROUPE:')
        self.stdout.write('-'*30)
        
        # Parcourt tous les groupes existants
        for group in Group.objects.all():
            self.stdout.write(f'\n{group.name.upper()}:')
            permissions = group.permissions.all()
            
            if permissions:
                # Affiche les 10 premières permissions pour éviter un output trop long
                for perm in permissions[:10]:
                    self.stdout.write(f'  - {perm.codename}')
                
                # Indique s'il y a plus de permissions non affichées
                if permissions.count() > 10:
                    self.stdout.write(f'  ... et {permissions.count() - 10} autres')
            else:
                self.stdout.write('  Aucune permission')
    
    def create_custom_permissions(self):
        """
        Crée des permissions personnalisées pour des fonctionnalités spécifiques.
        
        Cette méthode permet d'ajouter des permissions qui ne sont pas
        automatiquement générées par Django pour les modèles.
        
        Note: Cette méthode n'est pas appelée automatiquement.
        Elle peut être utilisée pour étendre le système de permissions.
        """
        
        # ========================================
        # CRÉATION DE PERMISSIONS PERSONNALISÉES
        # ========================================
        # ContentType représente le modèle auquel les permissions sont liées
        # Ici, on lie les permissions personnalisées au modèle CustomUser
        content_type = ContentType.objects.get_for_model(CustomUser)
        
        # Liste des permissions personnalisées à créer
        # Format: (codename, description_humaine)
        custom_permissions = [
            ('can_manage_users', 'Peut gérer les utilisateurs'),           # Gestion avancée des utilisateurs
            ('can_view_analytics', 'Peut voir les analyses'),              # Accès aux tableaux de bord
            ('can_manage_subscriptions', 'Peut gérer les abonnements'),    # Administration des abonnements
        ]
        
        # Création de chaque permission personnalisée
        for codename, name in custom_permissions:
            # get_or_create() évite les doublons
            # Retourne (permission, created) où created indique si l'objet a été créé
            permission, created = Permission.objects.get_or_create(
                codename=codename,        # Nom technique de la permission
                name=name,               # Description lisible
                content_type=content_type, # Modèle associé
            )
            
            # Affichage uniquement si la permission a été nouvellement créée
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Permission personnalisée créée: {name}')
                )