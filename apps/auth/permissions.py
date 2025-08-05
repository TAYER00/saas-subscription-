from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden


def admin_required(view_func):
    """Décorateur pour restreindre l'accès aux administrateurs uniquement."""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, 'Accès refusé. Vous devez être administrateur pour accéder à cette page.')
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def client_required(view_func):
    """Décorateur pour restreindre l'accès aux clients uniquement."""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_client:
            messages.error(request, 'Accès refusé. Cette page est réservée aux clients.')
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def group_required(*group_names):
    """Décorateur pour restreindre l'accès aux utilisateurs d'un ou plusieurs groupes."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not any(request.user.has_group(group) for group in group_names):
                messages.error(request, f'Accès refusé. Vous devez appartenir à l\'un de ces groupes: {", ".join(group_names)}')
                return redirect('dashboard:index')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def permission_required_custom(permission_codename):
    """Décorateur pour vérifier une permission spécifique."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.has_perm(permission_codename):
                messages.error(request, f'Accès refusé. Permission requise: {permission_codename}')
                return redirect('dashboard:index')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


class AdminRequiredMixin:
    """Mixin pour les vues basées sur les classes - accès admin uniquement."""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('auth:login')
        
        if not request.user.is_admin:
            messages.error(request, 'Accès refusé. Vous devez être administrateur pour accéder à cette page.')
            return redirect('dashboard:index')
        
        return super().dispatch(request, *args, **kwargs)


class ClientRequiredMixin:
    """Mixin pour les vues basées sur les classes - accès client uniquement."""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('auth:login')
        
        if not request.user.is_client:
            messages.error(request, 'Accès refusé. Cette page est réservée aux clients.')
            return redirect('dashboard:index')
        
        return super().dispatch(request, *args, **kwargs)


class GroupRequiredMixin:
    """Mixin pour les vues basées sur les classes - accès par groupe."""
    required_groups = []
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('auth:login')
        
        if not any(request.user.has_group(group) for group in self.required_groups):
            messages.error(request, f'Accès refusé. Vous devez appartenir à l\'un de ces groupes: {", ".join(self.required_groups)}')
            return redirect('dashboard:index')
        
        return super().dispatch(request, *args, **kwargs)


class PermissionRequiredMixin:
    """Mixin pour les vues basées sur les classes - vérification de permission."""
    required_permission = None
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('auth:login')
        
        if self.required_permission and not request.user.has_perm(self.required_permission):
            messages.error(request, f'Accès refusé. Permission requise: {self.required_permission}')
            return redirect('dashboard:index')
        
        return super().dispatch(request, *args, **kwargs)


def check_user_permissions(user, required_permissions):
    """Fonction utilitaire pour vérifier les permissions d'un utilisateur."""
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    if isinstance(required_permissions, str):
        required_permissions = [required_permissions]
    
    return all(user.has_perm(perm) for perm in required_permissions)


def get_user_role_context(user):
    """Fonction utilitaire pour obtenir le contexte des rôles d'un utilisateur."""
    if not user.is_authenticated:
        return {
            'is_admin': False,
            'is_client': False,
            'user_groups': [],
            'can_manage_users': False,
            'can_view_admin_panel': False,
        }
    
    user_groups = [group.name for group in user.groups.all()]
    
    return {
        'is_admin': user.is_admin,
        'is_client': user.is_client,
        'user_groups': user_groups,
        'can_manage_users': user.has_perm('auth.change_user') or user.is_admin,
        'can_view_admin_panel': user.is_staff or user.is_admin,
        'can_manage_subscriptions': user.has_perm('subscription.change_subscription') or user.is_admin,
    }