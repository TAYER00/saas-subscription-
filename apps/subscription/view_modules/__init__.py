# -*- coding: utf-8 -*-
"""
Package des vues de gestion des abonnements.

Ce package contient toutes les vues liées aux abonnements :
- Vues de migration d'abonnements
- Vues d'administration
- Vues utilisateur
"""

from .migration_views import (
    migrate_to_paid_plan,
    renew_subscription,
    subscription_detail,
    admin_migration_dashboard,
    admin_migrate_user,
    cleanup_expired_permissions,
    UserPermissionListView,
    MigrationLogListView
)

__all__ = [
    'migrate_to_paid_plan',
    'renew_subscription', 
    'subscription_detail',
    'admin_migration_dashboard',
    'admin_migrate_user',
    'cleanup_expired_permissions',
    'UserPermissionListView',
    'MigrationLogListView'
]