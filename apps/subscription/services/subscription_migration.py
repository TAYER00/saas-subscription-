# -*- coding: utf-8 -*-
"""
Service de gestion des migrations d'abonnements et permissions temporaires.

Ce module fournit les services pour :
- Migrer un utilisateur d'un plan gratuit vers un plan payant
- Gérer les permissions temporaires
- Renouveler les abonnements
- Nettoyer les permissions expirées
"""

from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from datetime import timedelta
from typing import List, Optional, Dict, Any
import logging

from ..models import Subscription, Plan
from ..models_permissions import (
    PlanPermission, 
    UserTemporaryPermission, 
    PermissionMigrationLog
)
from apps.auth.models import CustomUser

# Configuration du logger
logger = logging.getLogger(__name__)


class SubscriptionMigrationService:
    """
    Service principal pour gérer les migrations d'abonnements.
    
    Ce service centralise toute la logique métier liée aux changements
    de plans d'abonnement et à la gestion des permissions temporaires.
    """
    
    @staticmethod
    def migrate_user_to_paid_plan(
        user: CustomUser, 
        new_plan: Plan, 
        duration_days: int = 30,
        auto_activate: bool = True
    ) -> Dict[str, Any]:
        """
        Migre un utilisateur d'un plan gratuit vers un plan payant.
        
        Args:
            user (CustomUser): L'utilisateur à migrer
            new_plan (Plan): Le nouveau plan payant
            duration_days (int): Durée de validité en jours (défaut: 30)
            auto_activate (bool): Active automatiquement l'abonnement
            
        Returns:
            Dict[str, Any]: Résultat de la migration avec détails
            
        Raises:
            ValidationError: Si la migration n'est pas possible
        """
        try:
            with transaction.atomic():
                # Vérifications préliminaires
                SubscriptionMigrationService._validate_migration(
                    user, new_plan
                )
                
                # Récupérer l'abonnement actuel
                current_subscription = SubscriptionMigrationService._get_current_subscription(user)
                old_plan = current_subscription.plan if current_subscription else None
                
                # Créer ou mettre à jour l'abonnement
                subscription = SubscriptionMigrationService._create_or_update_subscription(
                    user, new_plan, duration_days, auto_activate
                )
                
                # Révoquer les anciennes permissions temporaires
                revoked_permissions = SubscriptionMigrationService._revoke_old_permissions(
                    user, current_subscription
                )
                
                # Accorder les nouvelles permissions
                granted_permissions = SubscriptionMigrationService._grant_plan_permissions(
                    user, new_plan, subscription, duration_days
                )
                
                # Enregistrer la migration dans le journal
                SubscriptionMigrationService._log_migration(
                    user, old_plan, new_plan, subscription, granted_permissions
                )
                
                logger.info(
                    f"Migration réussie pour {user.email} vers le plan {new_plan.name}"
                )
                
                return {
                    'success': True,
                    'subscription': subscription,
                    'granted_permissions': granted_permissions,
                    'revoked_permissions': revoked_permissions,
                    'message': f'Migration vers le plan {new_plan.name} réussie'
                }
                
        except Exception as e:
            logger.error(
                f"Erreur lors de la migration de {user.email} vers {new_plan.name}: {str(e)}"
            )
            raise ValidationError(f"Erreur lors de la migration: {str(e)}")
    
    @staticmethod
    def renew_subscription(
        user: CustomUser, 
        duration_days: int = 30,
        extend_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Renouvelle l'abonnement d'un utilisateur.
        
        Args:
            user (CustomUser): L'utilisateur dont renouveler l'abonnement
            duration_days (int): Durée du renouvellement en jours
            extend_existing (bool): Étendre les permissions existantes ou les remplacer
            
        Returns:
            Dict[str, Any]: Résultat du renouvellement
            
        Raises:
            ValidationError: Si le renouvellement n'est pas possible
        """
        try:
            with transaction.atomic():
                # Récupérer l'abonnement actuel
                subscription = SubscriptionMigrationService._get_current_subscription(user)
                
                if not subscription:
                    raise ValidationError("Aucun abonnement actif trouvé")
                
                if subscription.plan.is_free:
                    raise ValidationError("Impossible de renouveler un plan gratuit")
                
                # Mettre à jour la date d'expiration de l'abonnement
                if extend_existing and subscription.end_date > timezone.now():
                    # Étendre à partir de la date d'expiration actuelle
                    subscription.end_date += timedelta(days=duration_days)
                else:
                    # Renouveler à partir d'aujourd'hui
                    subscription.start_date = timezone.now()
                    subscription.end_date = timezone.now() + timedelta(days=duration_days)
                
                subscription.is_active = True
                subscription.save()
                
                # Renouveler les permissions
                renewed_permissions = SubscriptionMigrationService._renew_permissions(
                    user, subscription, duration_days, extend_existing
                )
                
                # Enregistrer le renouvellement dans le journal
                for permission in renewed_permissions:
                    PermissionMigrationLog.objects.create(
                        user=user,
                        action='RENEW',
                        permission=permission.permission,
                        new_plan=subscription.plan,
                        subscription=subscription,
                        details=f'Renouvellement pour {duration_days} jours'
                    )
                
                logger.info(
                    f"Renouvellement réussi pour {user.email} - Plan {subscription.plan.name}"
                )
                
                return {
                    'success': True,
                    'subscription': subscription,
                    'renewed_permissions': renewed_permissions,
                    'message': f'Abonnement renouvelé pour {duration_days} jours'
                }
                
        except Exception as e:
            logger.error(
                f"Erreur lors du renouvellement pour {user.email}: {str(e)}"
            )
            raise ValidationError(f"Erreur lors du renouvellement: {str(e)}")
    
    @staticmethod
    def cleanup_expired_permissions() -> Dict[str, int]:
        """
        Nettoie les permissions expirées de tous les utilisateurs.
        
        Cette méthode doit être appelée périodiquement (par exemple via une tâche cron)
        pour maintenir la cohérence du système.
        
        Returns:
            Dict[str, int]: Statistiques du nettoyage
        """
        try:
            with transaction.atomic():
                # Récupérer toutes les permissions expirées et actives
                expired_permissions = UserTemporaryPermission.objects.filter(
                    is_active=True,
                    expires_at__lt=timezone.now()
                )
                
                count = expired_permissions.count()
                
                # Enregistrer l'expiration dans le journal
                for perm in expired_permissions:
                    PermissionMigrationLog.objects.create(
                        user=perm.user,
                        action='EXPIRE',
                        permission=perm.permission,
                        subscription=perm.subscription,
                        details='Expiration automatique'
                    )
                
                # Désactiver les permissions expirées
                expired_permissions.update(
                    is_active=False,
                    revoked_at=timezone.now()
                )
                
                logger.info(f"Nettoyage terminé: {count} permissions expirées désactivées")
                
                return {
                    'expired_permissions': count,
                    'message': f'{count} permissions expirées ont été nettoyées'
                }
                
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des permissions: {str(e)}")
            return {
                'expired_permissions': 0,
                'error': str(e)
            }
    
    @staticmethod
    def get_user_active_permissions(user: CustomUser) -> List[Permission]:
        """
        Récupère toutes les permissions actives d'un utilisateur.
        
        Args:
            user (CustomUser): L'utilisateur
            
        Returns:
            List[Permission]: Liste des permissions actives
        """
        active_temp_permissions = UserTemporaryPermission.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).select_related('permission')
        
        return [perm.permission for perm in active_temp_permissions]
    
    # Méthodes privées pour la logique interne
    
    @staticmethod
    def _validate_migration(user: CustomUser, new_plan: Plan) -> None:
        """
        Valide si la migration est possible.
        
        Args:
            user (CustomUser): L'utilisateur
            new_plan (Plan): Le nouveau plan
            
        Raises:
            ValidationError: Si la migration n'est pas valide
        """
        if not new_plan.is_active:
            raise ValidationError("Le plan de destination n'est pas actif")
        
        if new_plan.is_free:
            raise ValidationError("Impossible de migrer vers un plan gratuit")
        
        current_subscription = SubscriptionMigrationService._get_current_subscription(user)
        if current_subscription and current_subscription.plan == new_plan:
            raise ValidationError("L'utilisateur est déjà sur ce plan")
    
    @staticmethod
    def _get_current_subscription(user: CustomUser) -> Optional[Subscription]:
        """
        Récupère l'abonnement actuel de l'utilisateur.
        
        Args:
            user (CustomUser): L'utilisateur
            
        Returns:
            Optional[Subscription]: L'abonnement actuel ou None
        """
        return Subscription.objects.filter(
            user=user,
            is_active=True
        ).first()
    
    @staticmethod
    def _create_or_update_subscription(
        user: CustomUser, 
        plan: Plan, 
        duration_days: int, 
        auto_activate: bool
    ) -> Subscription:
        """
        Crée ou met à jour l'abonnement de l'utilisateur.
        
        Args:
            user (CustomUser): L'utilisateur
            plan (Plan): Le nouveau plan
            duration_days (int): Durée en jours
            auto_activate (bool): Activer automatiquement
            
        Returns:
            Subscription: L'abonnement créé ou mis à jour
        """
        # Désactiver les anciens abonnements
        Subscription.objects.filter(
            user=user,
            is_active=True
        ).update(is_active=False)
        
        # Créer le nouvel abonnement
        start_date = timezone.now()
        end_date = start_date + timedelta(days=duration_days)
        
        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            start_date=start_date,
            end_date=end_date,
            is_active=auto_activate
        )
        
        return subscription
    
    @staticmethod
    def _revoke_old_permissions(
        user: CustomUser, 
        old_subscription: Optional[Subscription]
    ) -> List[UserTemporaryPermission]:
        """
        Révoque les anciennes permissions temporaires.
        
        Args:
            user (CustomUser): L'utilisateur
            old_subscription (Optional[Subscription]): L'ancien abonnement
            
        Returns:
            List[UserTemporaryPermission]: Permissions révoquées
        """
        old_permissions = UserTemporaryPermission.objects.filter(
            user=user,
            is_active=True
        )
        
        revoked = list(old_permissions)
        
        for perm in old_permissions:
            perm.revoke()
            PermissionMigrationLog.objects.create(
                user=user,
                action='REVOKE',
                permission=perm.permission,
                old_plan=old_subscription.plan if old_subscription else None,
                subscription=old_subscription,
                details='Révocation lors de la migration'
            )
        
        return revoked
    
    @staticmethod
    def _grant_plan_permissions(
        user: CustomUser, 
        plan: Plan, 
        subscription: Subscription, 
        duration_days: int
    ) -> List[UserTemporaryPermission]:
        """
        Accorde les permissions du plan à l'utilisateur.
        
        Args:
            user (CustomUser): L'utilisateur
            plan (Plan): Le plan
            subscription (Subscription): L'abonnement
            duration_days (int): Durée en jours
            
        Returns:
            List[UserTemporaryPermission]: Permissions accordées
        """
        plan_permissions = PlanPermission.objects.filter(
            plan=plan,
            is_active=True
        ).select_related('permission')
        
        granted_permissions = []
        expires_at = timezone.now() + timedelta(days=duration_days)
        
        for plan_perm in plan_permissions:
            temp_perm = UserTemporaryPermission.objects.create(
                user=user,
                permission=plan_perm.permission,
                subscription=subscription,
                expires_at=expires_at
            )
            granted_permissions.append(temp_perm)
        
        return granted_permissions
    
    @staticmethod
    def _renew_permissions(
        user: CustomUser, 
        subscription: Subscription, 
        duration_days: int, 
        extend_existing: bool
    ) -> List[UserTemporaryPermission]:
        """
        Renouvelle les permissions de l'utilisateur.
        
        Args:
            user (CustomUser): L'utilisateur
            subscription (Subscription): L'abonnement
            duration_days (int): Durée en jours
            extend_existing (bool): Étendre les permissions existantes
            
        Returns:
            List[UserTemporaryPermission]: Permissions renouvelées
        """
        if extend_existing:
            # Étendre les permissions existantes
            existing_permissions = UserTemporaryPermission.objects.filter(
                user=user,
                subscription=subscription,
                is_active=True
            )
            
            for perm in existing_permissions:
                perm.extend_expiration(days=duration_days)
            
            return list(existing_permissions)
        else:
            # Révoquer et recréer les permissions
            SubscriptionMigrationService._revoke_old_permissions(user, subscription)
            return SubscriptionMigrationService._grant_plan_permissions(
                user, subscription.plan, subscription, duration_days
            )
    
    @staticmethod
    def _log_migration(
        user: CustomUser, 
        old_plan: Optional[Plan], 
        new_plan: Plan, 
        subscription: Subscription, 
        granted_permissions: List[UserTemporaryPermission]
    ) -> None:
        """
        Enregistre la migration dans le journal.
        
        Args:
            user (CustomUser): L'utilisateur
            old_plan (Optional[Plan]): L'ancien plan
            new_plan (Plan): Le nouveau plan
            subscription (Subscription): L'abonnement
            granted_permissions (List[UserTemporaryPermission]): Permissions accordées
        """
        for perm in granted_permissions:
            PermissionMigrationLog.objects.create(
                user=user,
                action='MIGRATE',
                permission=perm.permission,
                old_plan=old_plan,
                new_plan=new_plan,
                subscription=subscription,
                details=f'Migration de {old_plan.name if old_plan else "Aucun"} vers {new_plan.name}'
            )