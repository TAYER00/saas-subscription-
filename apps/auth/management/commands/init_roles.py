from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.auth.models import CustomUser


class Command(BaseCommand):
    help = 'Initialise les groupes et permissions pour le système SaaS'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Supprime et recrée tous les groupes existants',
        )
    
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(
                self.style.WARNING('Suppression des groupes existants...')
            )
            Group.objects.filter(name__in=['admin', 'client']).delete()
        
        # Création des groupes
        admin_group, admin_created = Group.objects.get_or_create(name='admin')
        client_group, client_created = Group.objects.get_or_create(name='client')
        
        if admin_created:
            self.stdout.write(
                self.style.SUCCESS('Groupe "admin" créé avec succès')
            )
        else:
            self.stdout.write('Groupe "admin" existe déjà')
        
        if client_created:
            self.stdout.write(
                self.style.SUCCESS('Groupe "client" créé avec succès')
            )
        else:
            self.stdout.write('Groupe "client" existe déjà')
        
        # Configuration des permissions pour les administrateurs
        admin_permissions = Permission.objects.all()
        admin_group.permissions.set(admin_permissions)
        
        self.stdout.write(
            f'Toutes les permissions ({admin_permissions.count()}) '
            'assignées au groupe "admin"'
        )
        
        # Configuration des permissions pour les clients
        client_permissions = Permission.objects.filter(
            codename__in=[
                # Permissions de base pour les clients
                'view_customuser',  # Voir son propre profil
                'change_customuser',  # Modifier son propre profil
                'view_userprofile',  # Voir son profil étendu
                'change_userprofile',  # Modifier son profil étendu
                
                # Permissions pour les abonnements
                'view_subscription',  # Voir les abonnements
                'add_subscription',  # S'abonner
                'change_subscription',  # Modifier son abonnement
                
                # Permissions pour les plans
                'view_plan',  # Voir les plans disponibles
            ]
        )
        
        client_group.permissions.set(client_permissions)
        
        self.stdout.write(
            f'{client_permissions.count()} permissions '
            'assignées au groupe "client"'
        )
        
        # Création d'un superutilisateur par défaut si aucun n'existe
        if not CustomUser.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING(
                    'Aucun superutilisateur trouvé. '
                    'Création d\'un compte administrateur par défaut...'
                )
            )
            
            admin_user = CustomUser.objects.create_superuser(
                email='admin@saas.com',
                password='admin123',
                first_name='Admin',
                last_name='System',
                user_type='admin'
            )
            
            admin_user.groups.add(admin_group)
            
            self.stdout.write(
                self.style.SUCCESS(
                    'Superutilisateur créé:\n'
                    'Email: admin@saas.com\n'
                    'Mot de passe: admin123\n'
                    'IMPORTANT: Changez ce mot de passe en production!'
                )
            )
        
        # Création d'un utilisateur client de test
        if not CustomUser.objects.filter(email='client@test.com').exists():
            client_user = CustomUser.objects.create_user(
                email='client@test.com',
                password='client123',
                first_name='Client',
                last_name='Test',
                user_type='client'
            )
            
            client_user.groups.add(client_group)
            
            self.stdout.write(
                self.style.SUCCESS(
                    'Utilisateur client de test créé:\n'
                    'Email: client@test.com\n'
                    'Mot de passe: client123'
                )
            )
        
        # Affichage du résumé
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('RÉSUMÉ DE L\'INITIALISATION'))
        self.stdout.write('='*50)
        
        self.stdout.write(f'Groupes créés: {Group.objects.count()}')
        self.stdout.write(f'Permissions totales: {Permission.objects.count()}')
        self.stdout.write(f'Utilisateurs admin: {CustomUser.objects.filter(user_type="admin").count()}')
        self.stdout.write(f'Utilisateurs client: {CustomUser.objects.filter(user_type="client").count()}')
        
        self.stdout.write('\nGroupes et permissions configurés avec succès!')
        
        # Affichage des permissions par groupe
        self.stdout.write('\n' + '-'*30)
        self.stdout.write('PERMISSIONS PAR GROUPE:')
        self.stdout.write('-'*30)
        
        for group in Group.objects.all():
            self.stdout.write(f'\n{group.name.upper()}:')
            permissions = group.permissions.all()
            if permissions:
                for perm in permissions[:10]:  # Afficher seulement les 10 premières
                    self.stdout.write(f'  - {perm.codename}')
                if permissions.count() > 10:
                    self.stdout.write(f'  ... et {permissions.count() - 10} autres')
            else:
                self.stdout.write('  Aucune permission')
    
    def create_custom_permissions(self):
        """Crée des permissions personnalisées si nécessaire."""
        # Exemple de création de permissions personnalisées
        content_type = ContentType.objects.get_for_model(CustomUser)
        
        custom_permissions = [
            ('can_manage_users', 'Peut gérer les utilisateurs'),
            ('can_view_analytics', 'Peut voir les analyses'),
            ('can_manage_subscriptions', 'Peut gérer les abonnements'),
        ]
        
        for codename, name in custom_permissions:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                name=name,
                content_type=content_type,
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Permission personnalisée créée: {name}')
                )