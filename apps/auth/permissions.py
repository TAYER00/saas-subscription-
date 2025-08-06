# ============================================================================
# SYSTÈME DE PERMISSIONS ET CONTRÔLE D'ACCÈS
# ============================================================================
# Ce fichier définit un système complet de gestion des permissions pour
# l'application SaaS, incluant des décorateurs et des mixins pour contrôler
# l'accès aux vues selon les rôles et permissions des utilisateurs.
#
# Composants principaux :
# - Décorateurs pour vues basées sur les fonctions
# - Mixins pour vues basées sur les classes
# - Fonctions utilitaires pour vérification des permissions

# ========================================
# IMPORTS DJANGO ET PYTHON
# ========================================
from functools import wraps                        # Pour préserver les métadonnées des fonctions décorées
from django.contrib.auth.decorators import login_required  # Décorateur d'authentification Django
from django.core.exceptions import PermissionDenied        # Exception pour permissions refusées
from django.shortcuts import redirect                      # Redirection HTTP
from django.contrib import messages                        # Système de messages Django
from django.http import HttpResponseForbidden              # Réponse HTTP 403


# ============================================================================
# DÉCORATEURS POUR VUES BASÉES SUR LES FONCTIONS
# ============================================================================
# Ces décorateurs s'appliquent aux vues définies comme des fonctions
# et vérifient les permissions avant d'exécuter la vue

def admin_required(view_func):
    """
    Décorateur pour restreindre l'accès aux administrateurs uniquement.
    
    Ce décorateur :
    - Vérifie que l'utilisateur est connecté (via @login_required)
    - Vérifie que l'utilisateur a le rôle 'admin'
    - Redirige vers le dashboard avec un message d'erreur si l'accès est refusé
    
    Usage :
        @admin_required
        def ma_vue_admin(request):
            # Code accessible uniquement aux admins
            pass
    
    Args:
        view_func: La fonction de vue à protéger
        
    Returns:
        La fonction de vue décorée avec vérification des permissions
    """
    @wraps(view_func)  # Préserve le nom et la docstring de la fonction originale
    @login_required    # S'assure que l'utilisateur est connecté
    def _wrapped_view(request, *args, **kwargs):
        # Vérification du rôle administrateur via la propriété is_admin du modèle CustomUser
        if not request.user.is_admin:
            # Affichage d'un message d'erreur à l'utilisateur
            messages.error(request, 'Accès refusé. Vous devez être administrateur pour accéder à cette page.')
            # Redirection vers la page d'accueil du dashboard
            return redirect('dashboard:index')
        
        # Si toutes les vérifications passent, exécute la vue originale
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def client_required(view_func):
    """
    Décorateur pour restreindre l'accès aux clients uniquement.
    
    Ce décorateur :
    - Vérifie que l'utilisateur est connecté
    - Vérifie que l'utilisateur a le rôle 'client'
    - Redirige avec un message d'erreur si l'accès est refusé
    
    Usage :
        @client_required
        def ma_vue_client(request):
            # Code accessible uniquement aux clients
            pass
    
    Args:
        view_func: La fonction de vue à protéger
        
    Returns:
        La fonction de vue décorée avec vérification du rôle client
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # Vérification du rôle client via la propriété is_client du modèle CustomUser
        if not request.user.is_client:
            messages.error(request, 'Accès refusé. Cette page est réservée aux clients.')
            return redirect('dashboard:index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def group_required(*group_names):
    """
    Décorateur pour restreindre l'accès aux utilisateurs d'un ou plusieurs groupes.
    
    Ce décorateur utilise le système de groupes Django pour contrôler l'accès.
    L'utilisateur doit appartenir à AU MOINS UN des groupes spécifiés.
    
    Usage :
        @group_required('admin', 'moderator')
        def ma_vue_groupe(request):
            # Code accessible aux admins OU aux modérateurs
            pass
            
        @group_required('premium_users')
        def ma_vue_premium(request):
            # Code accessible uniquement aux utilisateurs premium
            pass
    
    Args:
        *group_names: Noms des groupes autorisés (un ou plusieurs)
        
    Returns:
        Décorateur qui vérifie l'appartenance aux groupes
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # Vérification avec any() : l'utilisateur doit appartenir à AU MOINS UN groupe
            # has_group() est une méthode personnalisée du modèle CustomUser
            if not any(request.user.has_group(group) for group in group_names):
                messages.error(request, f'Accès refusé. Vous devez appartenir à l\'un de ces groupes: {", ".join(group_names)}')
                return redirect('dashboard:index')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def permission_required_custom(permission_codename):
    """
    Décorateur pour vérifier une permission spécifique.
    
    Ce décorateur utilise le système de permissions Django pour un contrôle
    d'accès granulaire basé sur des permissions spécifiques plutôt que sur des rôles.
    
    Usage :
        @permission_required_custom('subscription.add_subscription')
        def creer_abonnement(request):
            # Code accessible uniquement aux utilisateurs ayant la permission
            # de créer des abonnements
            pass
            
        @permission_required_custom('auth.change_user')
        def modifier_utilisateur(request):
            # Code accessible uniquement aux utilisateurs pouvant modifier d'autres utilisateurs
            pass
    
    Args:
        permission_codename: Nom de la permission au format 'app.action_model'
                           (ex: 'subscription.view_plan', 'auth.change_user')
        
    Returns:
        Décorateur qui vérifie la permission spécifiée
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # Vérification de la permission via has_perm() de Django
            # Cette méthode vérifie les permissions directes ET celles héritées des groupes
            if not request.user.has_perm(permission_codename):
                messages.error(request, f'Accès refusé. Permission requise: {permission_codename}')
                return redirect('dashboard:index')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# ============================================================================
# MIXINS POUR VUES BASÉES SUR LES CLASSES
# ============================================================================
# Ces mixins s'appliquent aux vues basées sur les classes (Class-Based Views)
# et surchargent la méthode dispatch() pour vérifier les permissions

class AdminRequiredMixin:
    """
    Mixin pour les vues basées sur les classes - accès admin uniquement.
    
    Ce mixin surcharge la méthode dispatch() qui est appelée avant toute
    autre méthode de la vue (get, post, etc.).
    
    Usage :
        class MaVueAdmin(AdminRequiredMixin, ListView):
            model = MonModele
            # Cette vue sera accessible uniquement aux administrateurs
            
        class MaVueAdminDetail(AdminRequiredMixin, DetailView):
            model = MonModele
            # Cette vue de détail sera aussi protégée
    
    Note :
        Ce mixin doit être placé AVANT la classe de vue Django dans l'héritage
        pour que la méthode dispatch() soit correctement surchargée.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """
        Méthode appelée avant toute autre méthode de la vue.
        Vérifie l'authentification et les permissions administrateur.
        
        Args:
            request: Objet HttpRequest
            *args: Arguments positionnels
            **kwargs: Arguments nommés
            
        Returns:
            HttpResponse: Redirection si accès refusé, sinon appel de la vue parente
        """
        # Vérification de l'authentification
        if not request.user.is_authenticated:
            return redirect('auth:login')
        
        # Vérification du rôle administrateur
        if not request.user.is_admin:
            messages.error(request, 'Accès refusé. Vous devez être administrateur pour accéder à cette page.')
            return redirect('dashboard:index')
        
        # Si toutes les vérifications passent, appel de la méthode dispatch() parente
        return super().dispatch(request, *args, **kwargs)


class ClientRequiredMixin:
    """
    Mixin pour les vues basées sur les classes - accès client uniquement.
    
    Similaire à AdminRequiredMixin mais pour les clients.
    Utile pour protéger des vues spécifiques aux fonctionnalités client.
    
    Usage :
        class MonTableauDeBord(ClientRequiredMixin, TemplateView):
            template_name = 'client/dashboard.html'
            # Accessible uniquement aux clients
            
        class MesAbonnements(ClientRequiredMixin, ListView):
            model = Subscription
            # Liste des abonnements accessible uniquement aux clients
    """
    
    def dispatch(self, request, *args, **kwargs):
        """
        Vérifie l'authentification et les permissions client.
        
        Args:
            request: Objet HttpRequest
            *args: Arguments positionnels
            **kwargs: Arguments nommés
            
        Returns:
            HttpResponse: Redirection si accès refusé, sinon appel de la vue parente
        """
        # Vérification de l'authentification
        if not request.user.is_authenticated:
            return redirect('auth:login')
        
        # Vérification du rôle client
        if not request.user.is_client:
            messages.error(request, 'Accès refusé. Cette page est réservée aux clients.')
            return redirect('dashboard:index')
        
        # Appel de la méthode dispatch() parente
        return super().dispatch(request, *args, **kwargs)


class GroupRequiredMixin:
    """
    Mixin pour les vues basées sur les classes - accès par groupe.
    
    Ce mixin permet de restreindre l'accès aux utilisateurs appartenant
    à des groupes spécifiques. Plus flexible que les mixins de rôle.
    
    Usage :
        class MaVueModerateur(GroupRequiredMixin, ListView):
            model = MonModele
            required_groups = ['admin', 'moderator']  # Admin OU modérateur
            
        class MaVuePremium(GroupRequiredMixin, DetailView):
            model = MonModele
            required_groups = ['premium_users']  # Uniquement utilisateurs premium
    
    Attributes:
        required_groups (list): Liste des noms de groupes autorisés
    """
    # Attribut de classe à surcharger dans les vues filles
    required_groups = []
    
    def dispatch(self, request, *args, **kwargs):
        """
        Vérifie l'authentification et l'appartenance aux groupes requis.
        
        Args:
            request: Objet HttpRequest
            *args: Arguments positionnels
            **kwargs: Arguments nommés
            
        Returns:
            HttpResponse: Redirection si accès refusé, sinon appel de la vue parente
        """
        # Vérification de l'authentification
        if not request.user.is_authenticated:
            return redirect('auth:login')
        
        # Vérification de l'appartenance à au moins un des groupes requis
        if not any(request.user.has_group(group) for group in self.required_groups):
            messages.error(request, f'Accès refusé. Vous devez appartenir à l\'un de ces groupes: {", ".join(self.required_groups)}')
            return redirect('dashboard:index')
        
        return super().dispatch(request, *args, **kwargs)


class PermissionRequiredMixin:
    """
    Mixin pour les vues basées sur les classes - vérification de permission.
    
    Ce mixin offre un contrôle d'accès granulaire basé sur des permissions
    spécifiques plutôt que sur des rôles ou groupes.
    
    Usage :
        class CreerAbonnement(PermissionRequiredMixin, CreateView):
            model = Subscription
            required_permission = 'subscription.add_subscription'
            
        class ModifierUtilisateur(PermissionRequiredMixin, UpdateView):
            model = CustomUser
            required_permission = 'auth.change_user'
    
    Attributes:
        required_permission (str): Nom de la permission requise au format 'app.action_model'
    """
    # Attribut de classe à surcharger dans les vues filles
    required_permission = None
    
    def dispatch(self, request, *args, **kwargs):
        """
        Vérifie l'authentification et la permission requise.
        
        Args:
            request: Objet HttpRequest
            *args: Arguments positionnels
            **kwargs: Arguments nommés
            
        Returns:
            HttpResponse: Redirection si accès refusé, sinon appel de la vue parente
        """
        # Vérification de l'authentification
        if not request.user.is_authenticated:
            return redirect('auth:login')
        
        # Vérification de la permission si elle est définie
        if self.required_permission and not request.user.has_perm(self.required_permission):
            messages.error(request, f'Accès refusé. Permission requise: {self.required_permission}')
            return redirect('dashboard:index')
        
        return super().dispatch(request, *args, **kwargs)


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================
# Ces fonctions fournissent des outils pour vérifier les permissions et
# récupérer le contexte des rôles utilisateur dans les templates.

def check_user_permissions(user, required_permissions):
    """
    Vérifie si l'utilisateur a toutes les permissions spécifiées.
    
    Cette fonction utilitaire permet de vérifier facilement si un utilisateur
    possède une ou plusieurs permissions. Utile dans les vues, templates ou
    autres parties du code où une vérification de permission est nécessaire.
    
    Args:
        user (CustomUser): L'utilisateur à vérifier
        required_permissions (str|list): Permission(s) à vérifier. Peut être:
            - Une chaîne pour une seule permission: 'auth.add_user'
            - Une liste pour plusieurs permissions: ['auth.add_user', 'auth.change_user']
    
    Returns:
        bool: True si l'utilisateur a toutes les permissions, False sinon
        
    Examples:
        # Vérification d'une seule permission
        if check_user_permissions(request.user, 'subscription.add_subscription'):
            # L'utilisateur peut créer des abonnements
            
        # Vérification de plusieurs permissions
        admin_perms = ['auth.add_user', 'auth.change_user', 'auth.delete_user']
        if check_user_permissions(request.user, admin_perms):
            # L'utilisateur a tous les droits d'administration des utilisateurs
    """
    # Vérification de l'authentification
    if not user.is_authenticated:
        return False
    
    # Les superutilisateurs ont toutes les permissions
    if user.is_superuser:
        return True
    
    # Conversion en liste si c'est une chaîne
    if isinstance(required_permissions, str):
        required_permissions = [required_permissions]
    
    # Vérification que l'utilisateur a TOUTES les permissions
    return all(user.has_perm(perm) for perm in required_permissions)


def get_user_role_context(user):
    """
    Retourne le contexte des rôles de l'utilisateur pour les templates.
    
    Cette fonction génère un dictionnaire contenant toutes les informations
    de rôles et permissions d'un utilisateur, formatées pour être utilisées
    facilement dans les templates Django.
    
    Args:
        user (CustomUser): L'utilisateur pour lequel récupérer le contexte
        
    Returns:
        dict: Dictionnaire contenant:
            - is_admin (bool): True si l'utilisateur est admin
            - is_client (bool): True si l'utilisateur est client
            - user_groups (list): Liste des noms de groupes de l'utilisateur
            - can_manage_users (bool): True si peut gérer les utilisateurs
            - can_view_admin_panel (bool): True si peut voir le panel admin
            - can_manage_subscriptions (bool): True si peut gérer les abonnements
            
    Usage dans les templates:
        {% load auth_extras %}
        {% get_user_role_context request.user as user_context %}
        
        {% if user_context.is_admin %}
            <a href="{% url 'admin:dashboard' %}">Administration</a>
        {% endif %}
        
        {% if user_context.can_manage_users %}
            <a href="{% url 'admin:users' %}">Gérer les utilisateurs</a>
        {% endif %}
        
    Usage dans les vues:
        context = get_user_role_context(request.user)
        if context['is_admin']:
            # Logique spécifique aux admins
    """
    # Gestion des utilisateurs non authentifiés
    if not user.is_authenticated:
        return {
            'is_admin': False,
            'is_client': False,
            'user_groups': [],
            'can_manage_users': False,
            'can_view_admin_panel': False,
        }
    
    # Récupération des groupes de l'utilisateur
    user_groups = [group.name for group in user.groups.all()]
    
    # Construction du contexte pour les utilisateurs authentifiés
    return {
        # Vérification des rôles principaux via les propriétés du modèle
        'is_admin': user.is_admin,
        'is_client': user.is_client,
        
        # Liste de tous les groupes de l'utilisateur
        'user_groups': user_groups,
        
        # Permissions dérivées pour l'interface utilisateur
        'can_manage_users': user.has_perm('auth.change_user') or user.is_admin,
        'can_view_admin_panel': user.is_staff or user.is_admin,
        'can_manage_subscriptions': user.has_perm('subscription.change_subscription') or user.is_admin,
    }