from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from functools import wraps
from apps.subscription.models import Subscription

def premium_required(view_func):
    """
    Décorateur pour vérifier si l'utilisateur a un plan premium.
    Redirige vers la page des plans si l'utilisateur n'est pas premium.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            user_subscription = Subscription.objects.get(user=request.user, status='active')
            if user_subscription.plan.plan_type != 'premium':
                raise PermissionDenied("Accès premium requis")
        except Subscription.DoesNotExist:
            raise PermissionDenied("Aucun abonnement trouvé")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def check_premium_access(user):
    """
    Fonction utilitaire pour vérifier l'accès premium d'un utilisateur.
    Retourne True si l'utilisateur a un plan premium, False sinon.
    """
    if not user.is_authenticated:
        return False
    
    try:
        user_subscription = Subscription.objects.get(user=user, status='active')
        return user_subscription.plan.plan_type == 'premium'
    except Subscription.DoesNotExist:
        return False

def get_user_subscription_info(user):
    """
    Retourne les informations d'abonnement de l'utilisateur.
    """
    if not user.is_authenticated:
        return None, False
    
    try:
        user_subscription = Subscription.objects.get(user=user, status='active')
        is_premium = user_subscription.plan.plan_type == 'premium'
        return user_subscription, is_premium
    except Subscription.DoesNotExist:
        return None, False

class TenderViewPermissions:
    """
    Classe pour gérer les permissions d'affichage des appels d'offres.
    """
    
    @staticmethod
    def can_view_full_details(user):
        """Vérifie si l'utilisateur peut voir tous les détails."""
        return check_premium_access(user)
    
    @staticmethod
    def can_download_documents(user):
        """Vérifie si l'utilisateur peut télécharger les documents."""
        return check_premium_access(user)
    
    @staticmethod
    def can_access_source_url(user):
        """Vérifie si l'utilisateur peut accéder aux URLs sources."""
        return check_premium_access(user)
    
    @staticmethod
    def can_use_advanced_filters(user):
        """Vérifie si l'utilisateur peut utiliser les filtres avancés."""
        return check_premium_access(user)
    
    @staticmethod
    def get_masked_fields_for_user(user):
        """Retourne la liste des champs à masquer pour l'utilisateur."""
        if check_premium_access(user):
            return []  # Aucun champ masqué pour les utilisateurs premium
        
        # Champs masqués pour les utilisateurs gratuits
        return [
            'title',
            'organization', 
            'reference',
            'category',
            'status',
            'deadline_date',
            'estimated_value',
            'description',
            'eligibility_criteria',
            'location',
            'contact_info',
            'submission_method',
            'language',
            'documents'
        ]