# -*- coding: utf-8 -*-
"""
Commande de gestion Django pour nettoyer les permissions expirées.

Cette commande peut être exécutée manuellement ou programmée via cron
pour maintenir la cohérence du système de permissions temporaires.

Usage:
    python manage.py cleanup_permissions
    python manage.py cleanup_permissions --batch-size 50
    python manage.py cleanup_permissions --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

from ...services import SubscriptionMigrationService
from ...utils import PermissionManager
from ...models_permissions import UserTemporaryPermission

# Configuration du logger
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Commande pour nettoyer les permissions temporaires expirées.
    
    Cette commande :
    - Identifie toutes les permissions expirées
    - Les désactive et les marque comme révoquées
    - Enregistre les actions dans le journal
    - Fournit des statistiques détaillées
    """
    
    help = 'Nettoie les permissions temporaires expirées du système'
    
    def add_arguments(self, parser):
        """
        Ajoute les arguments de la commande.
        
        Args:
            parser: Le parser d'arguments Django
        """
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Taille des lots pour le traitement (défaut: 100)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait nettoyé sans effectuer les modifications'
        )
        
        parser.add_argument(
            '--days-buffer',
            type=int,
            default=0,
            help='Nombre de jours de grâce avant de considérer une permission comme expirée (défaut: 0)'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Affiche des informations détaillées pendant le traitement'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force le nettoyage même si beaucoup de permissions seraient affectées'
        )
    
    def handle(self, *args, **options):
        """
        Point d'entrée principal de la commande.
        
        Args:
            *args: Arguments positionnels
            **options: Options de la commande
        """
        # Configuration des options
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        days_buffer = options['days_buffer']
        verbose = options['verbose']
        force = options['force']
        
        # Validation des arguments
        if batch_size <= 0:
            raise CommandError('La taille des lots doit être positive')
        
        if days_buffer < 0:
            raise CommandError('Le buffer de jours ne peut pas être négatif')
        
        # Configuration du niveau de verbosité
        if verbose:
            self.stdout.write(
                self.style.SUCCESS('Mode verbose activé')
            )
        
        # Calcul de la date limite d'expiration
        expiration_threshold = timezone.now() - timedelta(days=days_buffer)
        
        if verbose:
            self.stdout.write(
                f'Date limite d\'expiration: {expiration_threshold}'
            )
        
        try:
            # Analyse préliminaire
            analysis = self._analyze_expired_permissions(
                expiration_threshold, verbose
            )
            
            # Vérification de sécurité
            if not self._safety_check(analysis, force):
                return
            
            # Exécution du nettoyage
            if dry_run:
                self._dry_run_cleanup(analysis, batch_size, verbose)
            else:
                self._execute_cleanup(analysis, batch_size, verbose)
            
        except Exception as e:
            logger.error(f'Erreur lors du nettoyage des permissions: {str(e)}')
            raise CommandError(f'Erreur lors du nettoyage: {str(e)}')
    
    def _analyze_expired_permissions(self, expiration_threshold, verbose):
        """
        Analyse les permissions expirées avant le nettoyage.
        
        Args:
            expiration_threshold: Date limite d'expiration
            verbose: Mode verbose
            
        Returns:
            dict: Analyse des permissions expirées
        """
        if verbose:
            self.stdout.write('Analyse des permissions expirées...')
        
        # Permissions expirées mais encore actives
        expired_active = UserTemporaryPermission.objects.filter(
            is_active=True,
            expires_at__lt=expiration_threshold
        )
        
        # Permissions déjà désactivées mais sans date de révocation
        inactive_no_revoke = UserTemporaryPermission.objects.filter(
            is_active=False,
            revoked_at__isnull=True,
            expires_at__lt=expiration_threshold
        )
        
        # Statistiques par plan
        from django.db.models import Count
        by_plan = expired_active.values(
            'subscription__plan__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Statistiques par utilisateur
        by_user = expired_active.values(
            'user__email'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]  # Top 10
        
        analysis = {
            'expired_active_count': expired_active.count(),
            'inactive_no_revoke_count': inactive_no_revoke.count(),
            'total_to_process': expired_active.count() + inactive_no_revoke.count(),
            'by_plan': list(by_plan),
            'by_user': list(by_user),
            'expired_active_queryset': expired_active,
            'inactive_no_revoke_queryset': inactive_no_revoke
        }
        
        # Affichage des statistiques
        self.stdout.write(
            self.style.WARNING(
                f'Permissions expirées actives: {analysis["expired_active_count"]}'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f'Permissions inactives sans révocation: {analysis["inactive_no_revoke_count"]}'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f'Total à traiter: {analysis["total_to_process"]}'
            )
        )
        
        if verbose and analysis['by_plan']:
            self.stdout.write('\nRépartition par plan:')
            for plan_stat in analysis['by_plan']:
                self.stdout.write(
                    f'  - {plan_stat["subscription__plan__name"]}: '
                    f'{plan_stat["count"]} permissions'
                )
        
        return analysis
    
    def _safety_check(self, analysis, force):
        """
        Vérifie la sécurité avant d'effectuer le nettoyage.
        
        Args:
            analysis: Résultats de l'analyse
            force: Mode forcé
            
        Returns:
            bool: True si le nettoyage peut continuer
        """
        total_to_process = analysis['total_to_process']
        
        # Seuil de sécurité : plus de 1000 permissions à traiter
        safety_threshold = 1000
        
        if total_to_process > safety_threshold and not force:
            self.stdout.write(
                self.style.ERROR(
                    f'ATTENTION: {total_to_process} permissions seraient affectées.\n'
                    f'Cela dépasse le seuil de sécurité de {safety_threshold}.\n'
                    f'Utilisez --force pour continuer ou vérifiez votre configuration.'
                )
            )
            return False
        
        if total_to_process == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    'Aucune permission expirée à nettoyer. Le système est à jour.'
                )
            )
            return False
        
        return True
    
    def _dry_run_cleanup(self, analysis, batch_size, verbose):
        """
        Simule le nettoyage sans effectuer de modifications.
        
        Args:
            analysis: Résultats de l'analyse
            batch_size: Taille des lots
            verbose: Mode verbose
        """
        self.stdout.write(
            self.style.WARNING('=== MODE DRY-RUN - AUCUNE MODIFICATION ===\n')
        )
        
        total_to_process = analysis['total_to_process']
        estimated_batches = (total_to_process + batch_size - 1) // batch_size
        
        self.stdout.write(f'Permissions à traiter: {total_to_process}')
        self.stdout.write(f'Taille des lots: {batch_size}')
        self.stdout.write(f'Nombre estimé de lots: {estimated_batches}')
        
        if verbose:
            self.stdout.write('\nDétail des permissions qui seraient nettoyées:')
            
            # Afficher quelques exemples
            sample_permissions = analysis['expired_active_queryset'][:10]
            for perm in sample_permissions:
                self.stdout.write(
                    f'  - {perm.user.email}: {perm.permission.name} '
                    f'(expiré le {perm.expires_at})'
                )
            
            if analysis['expired_active_count'] > 10:
                self.stdout.write(
                    f'  ... et {analysis["expired_active_count"] - 10} autres'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                '\n=== FIN DU DRY-RUN ===\n'
                'Utilisez la commande sans --dry-run pour effectuer le nettoyage.'
            )
        )
    
    def _execute_cleanup(self, analysis, batch_size, verbose):
        """
        Exécute le nettoyage réel des permissions expirées.
        
        Args:
            analysis: Résultats de l'analyse
            batch_size: Taille des lots
            verbose: Mode verbose
        """
        self.stdout.write(
            self.style.SUCCESS('Début du nettoyage des permissions expirées...')
        )
        
        start_time = timezone.now()
        
        try:
            # Utiliser le service de migration pour le nettoyage par lots
            if batch_size > 1:
                result = PermissionManager.cleanup_expired_permissions_batch(
                    batch_size=batch_size
                )
            else:
                # Nettoyage standard pour les petits volumes
                result = SubscriptionMigrationService.cleanup_expired_permissions()
            
            # Affichage des résultats
            end_time = timezone.now()
            duration = end_time - start_time
            
            if 'error' in result:
                self.stdout.write(
                    self.style.ERROR(
                        f'Erreur lors du nettoyage: {result["error"]}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Nettoyage terminé avec succès!\n'
                        f'Permissions nettoyées: {result.get("expired_permissions", result.get("total_cleaned", 0))}\n'
                        f'Durée: {duration.total_seconds():.2f} secondes'
                    )
                )
                
                if verbose and 'batches_processed' in result:
                    self.stdout.write(
                        f'Lots traités: {result["batches_processed"]}'
                    )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'Erreur lors de l\'exécution du nettoyage: {str(e)}'
                )
            )
            raise
        
        # Vérification post-nettoyage
        if verbose:
            self._post_cleanup_verification()
    
    def _post_cleanup_verification(self):
        """
        Vérifie l'état du système après le nettoyage.
        """
        self.stdout.write('\nVérification post-nettoyage...')
        
        # Compter les permissions encore expirées et actives
        remaining_expired = UserTemporaryPermission.objects.filter(
            is_active=True,
            expires_at__lt=timezone.now()
        ).count()
        
        # Compter les permissions actives valides
        active_valid = UserTemporaryPermission.objects.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        ).count()
        
        if remaining_expired > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'ATTENTION: {remaining_expired} permissions expirées '
                    f'sont encore actives. Vérifiez la configuration.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    'Toutes les permissions expirées ont été nettoyées.'
                )
            )
        
        self.stdout.write(
            f'Permissions actives valides: {active_valid}'
        )