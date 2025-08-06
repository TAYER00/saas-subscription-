# -*- coding: utf-8 -*-
"""
Package des utilitaires pour la gestion des abonnements.

Ce package contient tous les utilitaires liés aux abonnements :
- Gestion des permissions temporaires
- Tâches automatisées
- Décorateurs de permissions
- Rapports et statistiques
"""

from .permission_utils import (
    PermissionManager,
    require_temporary_permission
)

__all__ = [
    'PermissionManager',
    'require_temporary_permission'
]