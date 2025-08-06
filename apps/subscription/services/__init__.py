# -*- coding: utf-8 -*-
"""
Package des services de gestion des abonnements.

Ce package contient tous les services métier liés aux abonnements :
- Migration d'abonnements
- Gestion des permissions temporaires
- Renouvellement d'abonnements
- Utilitaires de gestion
"""

from .subscription_migration import SubscriptionMigrationService

__all__ = [
    'SubscriptionMigrationService',
]