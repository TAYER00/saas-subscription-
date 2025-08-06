# -*- coding: utf-8 -*-
"""
Utilitaires pour la gestion des permissions temporaires.

Ce module fournit des utilitaires pour :
- Créer et gérer les permissions personnalisées
- Vérifier les permissions d'un utilisateur
- Nettoyer automatiquement les permissions expirées
- Synchroniser les permissions avec les plans
"""

from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db import transaction
from typing import List, Dict, Optional, Tuple
import logging

from ..models import Plan
from ..models_permissions import (
    PlanPermission, 
    UserTemporaryPermission, 
    PermissionMigrationLog
)
from apps.auth.models import CustomUser

# Configuration du logger
logger = logging.getLogger(__name__)


class PermissionManager:
    """
    Gestionnaire principal pour les permissions temporaires.
    
    Cette classe centralise toutes les opérations liées aux permissions
    temporaires et à leur gestion automatisée.
    """
    
    # Permissions prédéfinies pour les plans payants
    PREMIUM_PERMISSIONS = {
        'advanced_analytics': {
            'name': 'Peut accéder aux analyses avancées',
            'codename': 'view_advanced_analytics',
            'content_type': 'subscription.subscription'
        },
        'export_data': {
            'name': 'Peut exporter les données',
            'codename': 'export_subscription_data',
            'content_type': 'subscription.subscription'
        },
        'priority_support': {
            'name': 'Accès au support prioritaire',
            'codename': 'access_priority_support',
            'content_type': 'auth.customuser'
        },
        'custom_branding': {
            'name': 'Peut personnaliser la marque',
            'codename': 'customize_branding',
            'content_type': 'subscription.subscription'
        },
        'api_access': {
            'name': 'Accès à l\'API avancée',
            'codename': 'access_advanced_api',
            'content_type': 'subscription.subscription'
        },
        'bulk_operations': {
            'name': 'Peut effectuer des opérations en lot',
            'codename': 'perform_bulk_operations',
            'content_type': 'subscription.subscription'
        }
    }
    
    @classmethod
    def create_premium_permissions(cls) -> Dict[str, Permission]:
        """
        Crée toutes les permissions premium prédéfinies.
        
        Returns:
            Dict[str, Permission]: Dictionnaire des permissions créées
        """
        created_permissions = {}
        
        with transaction.atomic():
            for key, perm_data in cls.PREMIUM_PERMISSIONS.items():
                try:
                    # Récupérer ou créer le content type
                    app_label, model = perm_data['content_type'].split('.')
                    content_type = ContentType.objects.get(
                        app_label=app_label,
                        model=model
                    )
                    
                    # Créer ou récupérer la permission
                    permission, created = Permission.objects.get_or_create(
                        codename=perm_data['codename'],
                        content_type=content_type,
                        defaults={'name': perm_data['name']}
                    )
                    
                    created_permissions[key] = permission
                    
                    if created:
                        logger.info(f"Permission créée: {permission.name}")
                    
                except Exception as e:
                    logger.error(f"Erreur lors de la création de la permission {key}: {str(e)}")
        
        return created_permissions
    
    @classmethod
    def assign_permissions_to_plan(
        cls, 
        plan: Plan, 
        permission_keys: List[str]
    ) -> List[PlanPermission]:
        """
        Assigne des permissions à un plan d'abonnement.
        
        Args:
            plan (Plan): Le plan d'abonnement
            permission_keys (List[str]): Liste des clés de permissions à assigner
            
        Returns:
            List[PlanPermission]: Liste des permissions assignées
        """
        assigned_permissions = []
        
        with transaction.atomic():
            for key in permission_keys:
                if key not in cls.PREMIUM_PERMISSIONS:
                    logger.warning(f"Permission inconnue: {key}")
                    continue
                
                try:
                    perm_data = cls.PREMIUM_PERMISSIONS[key]
                    app_label, model = perm_data['content_type'].split('.')
                    content_type = ContentType.objects.get(
                        app_label=app_label,
                        model=model
                    )
                    
                    permission = Permission.objects.get(
                        codename=perm_data['codename'],
                        content_type=content_type
                    )
                    
                    plan_permission, created = PlanPermission.objects.get_or_create(
                        plan=plan,
                        permission=permission,
                        defaults={'is_active': True}
                    )
                    
                    assigned_permissions.append(plan_permission)
                    
                    if created:
                        logger.info(
                            f"Permission {permission.name} assignée au plan {plan.name}"
                        )
                    
                except Exception as e:
                    logger.error(
                        f"Erreur lors de l'assignation de la permission {key} au plan {plan.name}: {str(e)}"
                    )
        
        return assigned_permissions
    
    @classmethod
    def check_user_permission(
        cls, 
        user: CustomUser, 
        permission_codename: str
    ) -> Tuple[bool, Optional[UserTemporaryPermission]]:
        """
        Vérifie si un utilisateur a une permission temporaire active.
        
        Args:
            user (CustomUser): L'utilisateur
            permission_codename (str): Le codename de la permission
            
        Returns:
            Tuple[bool, Optional[UserTemporaryPermission]]: 
                (a_la_permission, objet_permission_temporaire)
        """
        try:
            temp_permission = UserTemporaryPermission.objects.filter(
                user=user,
                permission__codename=permission_codename,
                is_active=True,
                expires_at__gt=timezone.now()
            ).first()
            
            return temp_permission is not None, temp_permission
            
        except Exception as e:
            logger.error(
                f"Erreur lors de la vérification de permission pour {user.email}: {str(e)}"
            )
            return False, None
    
    @classmethod
    def get_user_active_permissions(
        cls, 
        user: CustomUser
    ) -> List[Dict[str, any]]:
        """
        Récupère toutes les permissions temporaires actives d'un utilisateur.
        
        Args:
            user (CustomUser): L'utilisateur
            
        Returns:
            List[Dict[str, any]]: Liste des permissions avec détails
        """
        active_permissions = UserTemporaryPermission.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).select_related('permission', 'subscription__plan')
        
        permissions_data = []
        
        for perm in active_permissions:
            permissions_data.append({
                'id': perm.id,
                'name': perm.permission.name,
                'codename': perm.permission.codename,
                'granted_at': perm.granted_at,
                'expires_at': perm.expires_at,
                'plan_name': perm.subscription.plan.name,
                'days_remaining': (perm.expires_at - timezone.now()).days
            })
        
        return permissions_data
    
    @classmethod
    def sync_plan_permissions(cls, plan: Plan) -> Dict[str, int]:
        """
        Synchronise les permissions d'un plan avec les utilisateurs actifs.
        
        Cette méthode met à jour les permissions temporaires de tous les
        utilisateurs ayant un abonnement actif à ce plan.
        
        Args:
            plan (Plan): Le plan à synchroniser
            
        Returns:
            Dict[str, int]: Statistiques de synchronisation
        """
        stats = {
            'users_updated': 0,
            'permissions_granted': 0,
            'permissions_revoked': 0
        }
        
        try:
            with transaction.atomic():
                # Récupérer tous les abonnements actifs pour ce plan
                from ..models import Subscription
                active_subscriptions = Subscription.objects.filter(
                    plan=plan,
                    is_active=True,
                    end_date__gt=timezone.now()
                ).select_related('user')
                
                # Récupérer les permissions du plan
                plan_permissions = PlanPermission.objects.filter(
                    plan=plan,
                    is_active=True
                ).select_related('permission')
                
                for subscription in active_subscriptions:
                    user = subscription.user
                    stats['users_updated'] += 1
                    
                    # Récupérer les permissions temporaires actuelles
                    current_temp_perms = UserTemporaryPermission.objects.filter(
                        user=user,
                        subscription=subscription,
                        is_active=True
                    ).select_related('permission')
                    
                    current_perm_ids = set(
                        perm.permission.id for perm in current_temp_perms
                    )
                    plan_perm_ids = set(
                        perm.permission.id for perm in plan_permissions
                    )
                    
                    # Permissions à ajouter
                    to_add = plan_perm_ids - current_perm_ids
                    # Permissions à supprimer
                    to_remove = current_perm_ids - plan_perm_ids
                    
                    # Ajouter les nouvelles permissions
                    for plan_perm in plan_permissions:
                        if plan_perm.permission.id in to_add:
                            UserTemporaryPermission.objects.create(
                                user=user,
                                permission=plan_perm.permission,
                                subscription=subscription,
                                expires_at=subscription.end_date
                            )
                            stats['permissions_granted'] += 1
                    
                    # Supprimer les permissions obsolètes
                    for temp_perm in current_temp_perms:
                        if temp_perm.permission.id in to_remove:
                            temp_perm.revoke()
                            stats['permissions_revoked'] += 1
                
                logger.info(
                    f"Synchronisation du plan {plan.name} terminée: "
                    f"{stats['users_updated']} utilisateurs, "
                    f"{stats['permissions_granted']} permissions accordées, "
                    f"{stats['permissions_revoked']} permissions révoquées"
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation du plan {plan.name}: {str(e)}")
        
        return stats
    
    @classmethod
    def cleanup_expired_permissions_batch(
        cls, 
        batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Nettoie les permissions expirées par lots pour optimiser les performances.
        
        Args:
            batch_size (int): Taille des lots pour le traitement
            
        Returns:
            Dict[str, int]: Statistiques du nettoyage
        """
        stats = {
            'total_processed': 0,
            'total_cleaned': 0,
            'batches_processed': 0
        }
        
        try:
            while True:
                with transaction.atomic():
                    # Récupérer un lot de permissions expirées
                    expired_permissions = UserTemporaryPermission.objects.filter(
                        is_active=True,
                        expires_at__lt=timezone.now()
                    )[:batch_size]
                    
                    expired_list = list(expired_permissions)
                    
                    if not expired_list:
                        break  # Plus de permissions à traiter
                    
                    # Traiter le lot
                    for perm in expired_list:
                        # Enregistrer l'expiration dans le journal
                        PermissionMigrationLog.objects.create(
                            user=perm.user,
                            action='EXPIRE',
                            permission=perm.permission,
                            subscription=perm.subscription,
                            details='Expiration automatique par lot'
                        )
                        
                        # Désactiver la permission
                        perm.is_active = False
                        perm.revoked_at = timezone.now()
                        perm.save(update_fields=['is_active', 'revoked_at'])
                    
                    batch_count = len(expired_list)
                    stats['total_processed'] += batch_count
                    stats['total_cleaned'] += batch_count
                    stats['batches_processed'] += 1
                    
                    logger.info(
                        f"Lot {stats['batches_processed']} traité: "
                        f"{batch_count} permissions expirées nettoyées"
                    )
                    
                    # Si le lot est plus petit que la taille demandée, on a fini
                    if batch_count < batch_size:
                        break
            
            logger.info(
                f"Nettoyage par lots terminé: "
                f"{stats['total_cleaned']} permissions nettoyées en "
                f"{stats['batches_processed']} lots"
            )
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage par lots: {str(e)}")
        
        return stats
    
    @classmethod
    def generate_permissions_report(
        cls, 
        user: Optional[CustomUser] = None
    ) -> Dict[str, any]:
        """
        Génère un rapport détaillé sur les permissions temporaires.
        
        Args:
            user (Optional[CustomUser]): Utilisateur spécifique ou None pour tous
            
        Returns:
            Dict[str, any]: Rapport détaillé
        """
        report = {
            'generated_at': timezone.now(),
            'user_specific': user is not None,
            'statistics': {},
            'details': {}
        }
        
        try:
            # Filtrer par utilisateur si spécifié
            base_queryset = UserTemporaryPermission.objects.all()
            if user:
                base_queryset = base_queryset.filter(user=user)
                report['user_email'] = user.email
            
            # Statistiques générales
            report['statistics'] = {
                'total_permissions': base_queryset.count(),
                'active_permissions': base_queryset.filter(
                    is_active=True,
                    expires_at__gt=timezone.now()
                ).count(),
                'expired_permissions': base_queryset.filter(
                    is_active=False
                ).count(),
                'expiring_soon': base_queryset.filter(
                    is_active=True,
                    expires_at__lte=timezone.now() + timezone.timedelta(days=7),
                    expires_at__gt=timezone.now()
                ).count()
            }
            
            # Détails par plan
            if not user:
                from django.db.models import Count
                plan_stats = base_queryset.values(
                    'subscription__plan__name'
                ).annotate(
                    total=Count('id'),
                    active=Count('id', filter=models.Q(
                        is_active=True,
                        expires_at__gt=timezone.now()
                    ))
                ).order_by('-total')
                
                report['details']['by_plan'] = list(plan_stats)
            
            # Permissions les plus utilisées
            permission_stats = base_queryset.values(
                'permission__name',
                'permission__codename'
            ).annotate(
                total=Count('id')
            ).order_by('-total')[:10]
            
            report['details']['top_permissions'] = list(permission_stats)
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport: {str(e)}")
            report['error'] = str(e)
        
        return report


# Décorateur pour vérifier les permissions temporaires
def require_temporary_permission(permission_codename: str):
    """
    Décorateur pour vérifier qu'un utilisateur a une permission temporaire active.
    
    Args:
        permission_codename (str): Le codename de la permission requise
        
    Usage:
        @require_temporary_permission('view_advanced_analytics')
        def advanced_analytics_view(request):
            # Vue accessible uniquement avec la permission temporaire
            pass
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.decorators import login_required
                return login_required(view_func)(request, *args, **kwargs)
            
            has_permission, _ = PermissionManager.check_user_permission(
                request.user, permission_codename
            )
            
            if not has_permission:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied(
                    f"Permission temporaire requise: {permission_codename}"
                )
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator