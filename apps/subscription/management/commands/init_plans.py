from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.subscription.models import Plan


class Command(BaseCommand):
    help = 'Initialise les plans d\'abonnement par défaut'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initialisation des plans d\'abonnement...'))
        
        # Plan Gratuit (par défaut)
        free_plan, created = Plan.objects.get_or_create(
            slug='gratuit',
            defaults={
                'name': 'Plan Gratuit',
                'description': 'Plan de base gratuit avec fonctionnalités limitées',
                'plan_type': 'free',
                'price': 0.00,
                'billing_cycle': 'monthly',
                'max_users': 1,
                'max_projects': 3,
                'storage_limit_gb': 1,
                'has_api_access': False,
                'has_priority_support': False,
                'has_analytics': False,
                'has_custom_branding': False,
                'is_active': True,
                'is_featured': False,
                'sort_order': 1
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Plan "{free_plan.name}" créé'))
        else:
            self.stdout.write(self.style.WARNING(f'- Plan "{free_plan.name}" existe déjà'))
        
        # Plan Premium (payant)
        premium_plan, created = Plan.objects.get_or_create(
            slug='premium',
            defaults={
                'name': 'Plan Premium',
                'description': 'Plan avancé avec toutes les fonctionnalités premium',
                'plan_type': 'premium',
                'price': 29.99,
                'billing_cycle': 'monthly',
                'max_users': 0,  # Illimité
                'max_projects': 0,  # Illimité
                'storage_limit_gb': 0,  # Illimité
                'has_api_access': True,
                'has_priority_support': True,
                'has_analytics': True,
                'has_custom_branding': True,
                'is_active': True,
                'is_featured': True,
                'sort_order': 2
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Plan "{premium_plan.name}" créé'))
        else:
            self.stdout.write(self.style.WARNING(f'- Plan "{premium_plan.name}" existe déjà'))
        
        # Statistiques finales
        total_plans = Plan.objects.count()
        active_plans = Plan.objects.filter(is_active=True).count()
        
        self.stdout.write(self.style.SUCCESS('\n=== RÉSUMÉ DE L\'INITIALISATION ==='))
        self.stdout.write(f'Plans totaux: {total_plans}')
        self.stdout.write(f'Plans actifs: {active_plans}')
        self.stdout.write(f'Plan gratuit: {Plan.objects.filter(price=0).count()}')
        self.stdout.write(f'Plans payants: {Plan.objects.filter(price__gt=0).count()}')
        
        self.stdout.write(self.style.SUCCESS('\nInitialisation terminée avec succès!'))