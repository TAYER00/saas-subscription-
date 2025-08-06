# === IMPORTS DJANGO ===
# Raccourcis pour les vues
from django.shortcuts import render, get_object_or_404, redirect
# Décorateurs et mixins d'authentification
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
# Vues génériques basées sur les classes
from django.views.generic import ListView, DetailView, CreateView
# Système de messages pour les notifications utilisateur
from django.contrib import messages
# Réponses JSON pour les API
from django.http import JsonResponse
# Décorateurs pour limiter les méthodes HTTP
from django.views.decorators.http import require_http_methods
# Gestion des dates et heures avec timezone
from django.utils import timezone

# === IMPORTS LOCAUX ===
# Modèles de l'application subscription
from .models import Plan, Subscription, SubscriptionHistory
# Modèles pour les permissions temporaires
from .models_permissions import UserTemporaryPermission
# Permissions personnalisées pour les administrateurs
from apps.auth.permissions import admin_required, AdminRequiredMixin


class PlanListView(ListView):
    """
    Vue pour afficher la liste des plans d'abonnement disponibles.
    
    Cette vue :
    - Affiche uniquement les plans actifs
    - Trie les plans par ordre d'affichage puis par prix
    - Ajoute l'abonnement actuel de l'utilisateur au contexte
    - Permet la comparaison des plans
    
    Template : subscription/plans.html
    Contexte : plans, current_subscription, current_plan
    """
    model = Plan
    template_name = 'subscription/plans.html'
    context_object_name = 'plans'
    
    def get_queryset(self):
        """
        Retourne uniquement les plans actifs, triés par ordre d'affichage.
        
        Returns:
            QuerySet: Plans actifs triés par sort_order puis prix
        """
        return Plan.objects.filter(is_active=True).order_by('sort_order', 'price')
    
    def get_context_data(self, **kwargs):
        """
        Ajoute l'abonnement actuel de l'utilisateur au contexte.
        
        Permet d'afficher :
        - Le plan actuellement souscrit
        - Les boutons d'action appropriés (upgrade, downgrade)
        - Les comparaisons de fonctionnalités
        
        Returns:
            dict: Contexte enrichi avec current_subscription et current_plan
        """
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            # Récupérer l'abonnement actuel de l'utilisateur
            current_subscription = Subscription.objects.filter(
                user=self.request.user,
                status='active'
            ).first()
            context['current_subscription'] = current_subscription
            context['current_plan'] = current_subscription.plan if current_subscription else None
        
        return context


class PlanDetailView(DetailView):
    """
    Vue pour afficher les détails complets d'un plan d'abonnement.
    
    Cette vue :
    - Affiche toutes les informations d'un plan
    - Vérifie si l'utilisateur possède déjà ce plan
    - Propose les actions appropriées (souscription, changement)
    - Utilise le slug pour des URLs conviviales
    
    Template : subscription/plan_detail.html
    URL : /plans/<slug>/
    Contexte : plan, has_plan
    """
    model = Plan
    template_name = 'subscription/plan_detail.html'
    context_object_name = 'plan'
    slug_field = 'slug'  # Utilise le champ slug du modèle
    slug_url_kwarg = 'slug'  # Nom du paramètre dans l'URL
    
    def get_context_data(self, **kwargs):
        """
        Vérifie si l'utilisateur possède déjà ce plan.
        
        Permet d'adapter l'affichage :
        - Masquer le bouton de souscription si déjà souscrit
        - Afficher des informations sur l'abonnement actuel
        - Proposer des actions alternatives
        
        Returns:
            dict: Contexte enrichi avec has_plan
        """
        context = super().get_context_data(**kwargs)
        
        if self.request.user.is_authenticated:
            # Vérifier si l'utilisateur a déjà ce plan
            has_plan = Subscription.objects.filter(
                user=self.request.user,
                plan=self.object,
                status='active'
            ).exists()
            context['has_plan'] = has_plan
        
        return context


@login_required
def subscribe_to_plan(request, plan_id):
    """
    Vue pour gérer la souscription à un plan d'abonnement.
    
    Cette fonction :
    - Vérifie l'existence et l'activité du plan
    - Gère les abonnements existants (redirection vers changement)
    - Pour les plans gratuits : crée directement l'abonnement
    - Pour les plans payants : redirige vers la page de paiement
    - Enregistre l'historique de l'action
    
    Args:
        request: Requête HTTP
        plan_id (int): ID du plan à souscrire
    
    Returns:
        HttpResponse: Redirection vers payment, my_subscription ou change_plan
    
    Requires:
        - Utilisateur authentifié (@login_required)
        - Plan existant et actif
    """
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    
    # Vérifier si l'utilisateur a déjà un abonnement actif
    existing_subscription = Subscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    if existing_subscription:
        if existing_subscription.plan == plan:
            # L'utilisateur a déjà ce plan
            messages.info(request, f'Vous êtes déjà abonné au plan {plan.name}.')
            return redirect('subscription:my_subscription')
        else:
            # L'utilisateur a un autre plan : redirection vers changement
            return redirect('subscription:change_plan', plan_id=plan.id)
    
    # Vérifier si le plan est gratuit ou payant
    if plan.price == 0:
        # Plan gratuit : créer directement l'abonnement
        subscription = Subscription.objects.create(
            user=request.user,
            plan=plan,
            status='active',
            amount_paid=0.00
        )
        
        # Créer une entrée dans l'historique
        SubscriptionHistory.objects.create(
            subscription=subscription,
            action='created',
            new_plan=plan,
            notes=f'Abonnement gratuit au plan {plan.name}'
        )
        
        messages.success(
            request,
            f'Félicitations! Vous êtes maintenant abonné au plan {plan.name}.'
        )
        return redirect('subscription:my_subscription')
    else:
        # Plan payant : rediriger vers la page de paiement
        return redirect('subscription:payment', plan_id=plan.id)


@login_required
def payment_page(request, plan_id):
    """
    Vue pour afficher la page de paiement d'un plan premium.
    
    Cette fonction :
    - Vérifie que le plan existe et est payant
    - Affiche les détails du plan et le formulaire de paiement
    - Traite le paiement (simulation)
    - Crée l'abonnement après paiement réussi
    
    Args:
        request: Requête HTTP
        plan_id (int): ID du plan à payer
    
    Returns:
        HttpResponse: Page de paiement ou redirection
    
    Requires:
        - Utilisateur authentifié (@login_required)
        - Plan existant et payant
    """
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    
    # Vérifier que le plan est payant
    if plan.price == 0:
        messages.error(request, 'Ce plan est gratuit, aucun paiement requis.')
        return redirect('subscription:subscribe', plan_id=plan.id)
    
    # Vérifier si l'utilisateur a déjà un abonnement actif
    existing_subscription = Subscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    if request.method == 'POST':
        # Simulation du traitement de paiement
        payment_method = request.POST.get('payment_method')
        card_number = request.POST.get('card_number')
        
        if not payment_method or not card_number:
            messages.error(request, 'Veuillez remplir tous les champs de paiement.')
        else:
            # Simulation d'un paiement réussi
            # Dans un vrai projet, ici on intégrerait Stripe, PayPal, etc.
            
            # Annuler l'abonnement existant s'il y en a un
            if existing_subscription:
                existing_subscription.status = 'cancelled'
                existing_subscription.save()
                
                SubscriptionHistory.objects.create(
                    subscription=existing_subscription,
                    action='cancelled',
                    old_plan=existing_subscription.plan,
                    notes='Annulé pour upgrade vers plan premium'
                )
            
            # Créer le nouvel abonnement premium
            subscription = Subscription.objects.create(
                user=request.user,
                plan=plan,
                status='active',
                amount_paid=plan.price
            )
            
            # Créer une entrée dans l'historique
            SubscriptionHistory.objects.create(
                subscription=subscription,
                action='created',
                new_plan=plan,
                notes=f'Abonnement premium payé - {payment_method}'
            )
            
            messages.success(
                request,
                f'Paiement réussi! Vous êtes maintenant abonné au plan {plan.name}.'
            )
            return redirect('subscription:my_subscription')
    
    context = {
        'plan': plan,
        'existing_subscription': existing_subscription,
    }
    
    return render(request, 'subscription/payment.html', context)


@login_required
def change_plan(request, plan_id):
    """
    Vue pour gérer le changement de plan d'abonnement (upgrade/downgrade).
    
    Cette fonction :
    - Vérifie l'existence d'un abonnement actuel
    - Valide le nouveau plan demandé
    - Empêche les utilisateurs réguliers de passer d'un plan payant à gratuit
    - Met à jour l'abonnement existant
    - Enregistre l'historique du changement
    - Calcule les différences de prix si nécessaire
    
    Args:
        request: Requête HTTP
        plan_id (int): ID du nouveau plan souhaité
    
    Returns:
        HttpResponse: Redirection vers my_subscription ou plans
    
    Requires:
        - Utilisateur authentifié (@login_required)
        - Abonnement actif existant
        - Nouveau plan existant et actif
    """
    new_plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    
    # Récupérer l'abonnement actuel de l'utilisateur
    current_subscription = Subscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    if not current_subscription:
        messages.error(request, 'Vous n\'avez pas d\'abonnement actif.')
        return redirect('subscription:plans')
    
    if current_subscription.plan == new_plan:
        messages.info(request, f'Vous êtes déjà abonné au plan {new_plan.name}.')
        return redirect('subscription:my_subscription')
    
    old_plan = current_subscription.plan
    
    # Vérifier si l'utilisateur régulier essaie de passer d'un plan payant à gratuit
    if not request.user.is_staff:  # Utilisateur régulier (non admin)
        if old_plan.price > 0 and new_plan.price == 0:  # De payant vers gratuit
            messages.error(
                request, 
                'Vous ne pouvez pas passer directement d\'un abonnement payant vers un abonnement gratuit. '
                'Votre abonnement payant expirera automatiquement à la fin de sa période. '
                'Vous pouvez utiliser le bouton "Annuler l\'abonnement" pour passer au plan gratuit.'
            )
            return redirect('subscription:my_subscription')
    
    # Mettre à jour l'abonnement
    current_subscription.plan = new_plan
    current_subscription.amount_paid = new_plan.price
    current_subscription.save()
    
    # Déterminer le type d'action
    if new_plan.price > old_plan.price:
        action = 'upgraded'
        message = f'Votre plan a été mis à niveau vers {new_plan.name}.'
    else:
        action = 'downgraded'
        message = f'Votre plan a été rétrogradé vers {new_plan.name}.'
    
    # Créer un historique
    SubscriptionHistory.objects.create(
        subscription=current_subscription,
        action=action,
        old_plan=old_plan,
        new_plan=new_plan,
        notes=f'Changement de plan de {old_plan.name} vers {new_plan.name}'
    )
    
    messages.success(request, message)
    return redirect('subscription:my_subscription')


@login_required
def my_subscription(request):
    """
    Vue pour afficher l'abonnement actuel de l'utilisateur.
    
    Cette fonction :
    - Récupère l'abonnement actif de l'utilisateur
    - Affiche l'historique des 10 dernières actions
    - Liste les plans disponibles pour changement
    - Fournit les informations de facturation et d'expiration
    
    Args:
        request: Requête HTTP
    
    Returns:
        HttpResponse: Page de gestion de l'abonnement
    
    Template : subscription/my_subscription.html
    URL : /my-subscription/
    Contexte : subscription, subscription_history, available_plans
    """
    # Récupérer l'abonnement actif de l'utilisateur
    subscription = Subscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    # Récupérer l'historique des actions (10 dernières entrées)
    subscription_history = SubscriptionHistory.objects.filter(
        subscription__user=request.user
    ).order_by('-created_at')[:10] if subscription else []
    
    # Préparer le contexte pour le template
    context = {
        'subscription': subscription,  # Abonnement actuel
        'subscription_history': subscription_history,  # Historique des actions
        'available_plans': Plan.objects.filter(is_active=True).exclude(
            id=subscription.plan.id if subscription else None
        )  # Plans disponibles pour changement (excluant le plan actuel)
    }
    
    return render(request, 'subscription/my_subscription.html', context)


@login_required
def cancel_subscription(request):
    """
    Vue pour annuler l'abonnement payant et passer au plan gratuit.
    
    Cette fonction :
    - Vérifie que la requête est en POST (sécurité)
    - Trouve l'abonnement actif de l'utilisateur
    - Passe l'utilisateur au plan gratuit (Free)
    - Enregistre l'action dans l'historique
    - Affiche un message de confirmation
    
    Args:
        request: Requête HTTP (doit être POST)
    
    Returns:
        HttpResponse: Redirection vers my_subscription
    
    Requires:
        - Utilisateur authentifié (@login_required)
        - Méthode POST pour la sécurité
        - Abonnement actif existant
        - Plan gratuit existant
    """
    if request.method == 'POST':
        # Récupérer l'abonnement actif de l'utilisateur
        subscription = Subscription.objects.filter(
            user=request.user,
            status='active'
        ).first()
        
        if subscription:
            # Vérifier que c'est un abonnement payant
            if subscription.plan.price > 0:
                # Trouver le plan gratuit
                try:
                    free_plan = Plan.objects.filter(price=0, is_active=True).first()
                    if not free_plan:
                        messages.error(request, 'Aucun plan gratuit disponible.')
                        return redirect('subscription:my_subscription')
                    
                    old_plan = subscription.plan
                    
                    # Passer au plan gratuit
                    subscription.plan = free_plan
                    subscription.amount_paid = 0
                    subscription.save()
                    
                    # Créer une entrée dans l'historique pour traçabilité
                    SubscriptionHistory.objects.create(
                        subscription=subscription,
                        action='cancelled',  # Type d'action
                        old_plan=old_plan,  # Plan qui était actif
                        new_plan=free_plan,  # Nouveau plan gratuit
                        notes=f'Abonnement payant {old_plan.name} annulé, passage au plan gratuit {free_plan.name}'
                    )
                    
                    # Message de confirmation pour l'utilisateur
                    messages.success(
                        request,
                        f'Votre abonnement {old_plan.name} a été annulé avec succès. '
                        f'Vous êtes maintenant sur le plan gratuit {free_plan.name}.'
                    )
                except Exception as e:
                    messages.error(request, 'Erreur lors de l\'annulation de l\'abonnement.')
            else:
                messages.info(request, 'Vous êtes déjà sur un plan gratuit.')
        else:
            # Aucun abonnement actif trouvé
            messages.error(request, 'Aucun abonnement actif trouvé.')
    
    # Redirection vers la page de gestion de l'abonnement
    return redirect('subscription:my_subscription')


@login_required
def renew_subscription(request):
    """
    Vue pour renouveler un abonnement annulé ou expiré.
    
    Cette fonction :
    - Vérifie que la requête est en POST (sécurité)
    - Trouve un abonnement annulé ou expiré de l'utilisateur
    - Appelle la méthode renew() du modèle
    - Enregistre l'action dans l'historique
    - Affiche un message de confirmation
    
    Args:
        request: Requête HTTP (doit être POST)
    
    Returns:
        HttpResponse: Redirection vers my_subscription
    
    Requires:
        - Utilisateur authentifié (@login_required)
        - Méthode POST pour la sécurité
        - Abonnement annulé ou expiré existant
    """
    if request.method == 'POST':
        # Récupérer un abonnement annulé ou expiré de l'utilisateur
        subscription = Subscription.objects.filter(
            user=request.user,
            status__in=['cancelled', 'expired']  # Statuts éligibles au renouvellement
        ).first()
        
        if subscription:
            # Renouveler l'abonnement (remet le statut à 'active')
            subscription.renew()
            
            # Créer une entrée dans l'historique pour traçabilité
            SubscriptionHistory.objects.create(
                subscription=subscription,
                action='renewed',  # Type d'action
                new_plan=subscription.plan,  # Plan renouvelé
                notes='Abonnement renouvelé par l\'utilisateur'  # Note explicative
            )
            
            # Message de confirmation pour l'utilisateur
            messages.success(
                request,
                'Votre abonnement a été renouvelé avec succès.'
            )
        else:
            # Aucun abonnement éligible au renouvellement
            messages.error(request, 'Aucun abonnement à renouveler trouvé.')
    
    # Redirection vers la page de gestion de l'abonnement
    return redirect('subscription:my_subscription')


# ============================================================================
# VUES D'ADMINISTRATION
# ============================================================================
# Ces vues sont réservées aux administrateurs pour gérer les abonnements
# et les plans. Elles utilisent AdminRequiredMixin pour la sécurité.

class AdminSubscriptionListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    """
    Vue d'administration pour lister et gérer tous les abonnements.
    
    Cette vue :
    - Affiche tous les abonnements avec pagination
    - Fournit des statistiques globales (total, actifs, annulés)
    - Calcule le chiffre d'affaires total
    - Optimise les requêtes avec select_related
    
    Permissions:
        - AdminRequiredMixin : Seuls les admins peuvent accéder
        - LoginRequiredMixin : Utilisateur authentifié requis
    
    Template : subscription/admin/subscription_list.html
    URL : /admin/subscriptions/
    Contexte : subscriptions, total_subscriptions, active_subscriptions, 
               cancelled_subscriptions, total_revenue
    """
    model = Subscription
    template_name = 'subscription/admin/subscription_list.html'
    context_object_name = 'subscriptions'
    paginate_by = 20  # 20 abonnements par page
    
    def get_queryset(self):
        """
        Optimise les requêtes en préchargeant les relations.
        
        Returns:
            QuerySet: Abonnements avec utilisateurs et plans préchargés
        """
        return Subscription.objects.select_related('user', 'plan').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """
        Ajoute des statistiques globales au contexte.
        
        Returns:
            dict: Contexte enrichi avec les statistiques
        """
        context = super().get_context_data(**kwargs)
        
        # Statistiques générales pour le tableau de bord admin
        context['total_subscriptions'] = Subscription.objects.count()
        context['active_subscriptions'] = Subscription.objects.filter(status='active').count()
        context['cancelled_subscriptions'] = Subscription.objects.filter(status='cancelled').count()
        context['total_revenue'] = sum(
            sub.amount_paid for sub in Subscription.objects.filter(status='active')
        )
        
        return context


class AdminPlanListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    """
    Vue d'administration pour gérer les plans d'abonnement.
    
    Cette vue :
    - Affiche tous les plans (actifs et inactifs)
    - Calcule les statistiques par plan (abonnés, revenus)
    - Permet l'activation/désactivation des plans
    - Fournit une vue d'ensemble de la performance des plans
    
    Permissions:
        - AdminRequiredMixin : Seuls les admins peuvent accéder
        - LoginRequiredMixin : Utilisateur authentifié requis
    
    Template : subscription/admin/plan_list.html
    URL : /admin/plans/
    Contexte : plans (avec subscription_count et total_revenue ajoutés)
    """
    model = Plan
    template_name = 'subscription/admin/plan_list.html'
    context_object_name = 'plans'
    
    def get_context_data(self, **kwargs):
        """
        Enrichit chaque plan avec ses statistiques.
        
        Returns:
            dict: Contexte avec plans et leurs métriques
        """
        context = super().get_context_data(**kwargs)
        
        # Ajouter des statistiques à chaque plan
        for plan in context['plans']:
            # Nombre d'abonnements actifs pour ce plan
            plan.subscription_count = plan.subscriptions.filter(status='active').count()
            # Revenus générés par ce plan
            plan.total_revenue = sum(
                sub.amount_paid for sub in plan.subscriptions.filter(status='active')
            )
        
        return context


@admin_required
def toggle_plan_status(request, plan_id):
    """
    Vue d'administration pour activer/désactiver un plan.
    
    Cette fonction :
    - Bascule le statut is_active du plan
    - Supporte les requêtes AJAX et normales
    - Affiche un message de confirmation
    - Redirige vers la liste des plans admin
    
    Args:
        request: Requête HTTP
        plan_id (int): ID du plan à modifier
    
    Returns:
        JsonResponse: Si requête AJAX avec statut et message
        HttpResponse: Redirection vers admin_plans sinon
    
    Requires:
        - Permissions administrateur (@admin_required)
        - Plan existant
    """
    # Récupérer le plan ou retourner 404
    plan = get_object_or_404(Plan, id=plan_id)
    
    # Basculer le statut actif/inactif
    plan.is_active = not plan.is_active
    plan.save()
    
    # Préparer le message de confirmation
    status = 'activé' if plan.is_active else 'désactivé'
    messages.success(request, f'Plan {plan.name} {status} avec succès.')
    
    # Réponse différente selon le type de requête
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Requête AJAX : retourner JSON
        return JsonResponse({
            'success': True,
            'message': f'Plan {status}',
            'is_active': plan.is_active
        })
    
    # Requête normale : redirection
    return redirect('subscription:admin_plans')


# ============================================================================
# API ENDPOINTS
# ============================================================================
# Points d'accès API pour les informations d'abonnement

@require_http_methods(["GET"])
@login_required
def subscription_api(request):
    """
    API endpoint pour récupérer les informations d'abonnement de l'utilisateur.
    
    Cette API :
    - Retourne les détails de l'abonnement actif
    - Fournit les informations du plan et des fonctionnalités
    - Calcule les jours restants automatiquement
    - Supporte uniquement les requêtes GET
    
    Args:
        request: Requête HTTP (GET uniquement)
    
    Returns:
        JsonResponse: Données d'abonnement au format JSON
        
        Structure de réponse avec abonnement :
        {
            'has_subscription': True,
            'plan_name': str,
            'plan_type': str,
            'status': str,
            'start_date': str (ISO format),
            'end_date': str (ISO format) ou None,
            'days_remaining': int,
            'is_trial': bool,
            'features': list
        }
        
        Structure de réponse sans abonnement :
        {
            'has_subscription': False,
            'plan_name': None,
            'plan_type': None,
            'status': None
        }
    
    Requires:
        - Utilisateur authentifié (@login_required)
        - Méthode GET uniquement (@require_http_methods)
    
    Usage:
        GET /api/subscription/
        Content-Type: application/json
    """
    # Récupérer l'abonnement actif de l'utilisateur
    subscription = Subscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    if subscription:
        # Utilisateur avec abonnement actif
        data = {
            'has_subscription': True,
            'plan_name': subscription.plan.name,  # Nom du plan
            'plan_type': subscription.plan.plan_type,  # Type (free, basic, premium)
            'status': subscription.status,  # Statut de l'abonnement
            'start_date': subscription.start_date.isoformat(),  # Date de début (ISO)
            'end_date': subscription.end_date.isoformat() if subscription.end_date else None,  # Date de fin
            'days_remaining': subscription.days_remaining,  # Jours restants (calculé)
            'is_trial': subscription.is_trial,  # Période d'essai
            'features': subscription.plan.get_features_list(),  # Liste des fonctionnalités
        }
    else:
        # Utilisateur sans abonnement actif
        data = {
            'has_subscription': False,
            'plan_name': None,
            'plan_type': None,
            'status': None,
        }
    
    return JsonResponse(data)


@login_required
def test_permissions(request):
    """
    Vue de test pour afficher les permissions d'abonnement Premium.
    
    Cette vue :
    - Vérifie que l'utilisateur a un plan Premium actif
    - Affiche les permissions temporaires de l'utilisateur
    - Change la couleur de fond en jaune si l'utilisateur a des permissions payantes
    - Permet de tester visuellement le système de permissions
    
    Args:
        request: Requête HTTP
    
    Returns:
        HttpResponse: Page de test des permissions ou redirection si pas Premium
    
    Requires:
        - Utilisateur authentifié (@login_required)
        - Plan Premium actif
    """
    # Récupérer l'abonnement actuel de l'utilisateur
    current_subscription = Subscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    # Vérifier que l'utilisateur a un plan Premium
    if not current_subscription or current_subscription.plan.plan_type != 'premium':
        messages.error(
            request, 
            'Accès refusé. Cette fonctionnalité est réservée aux utilisateurs Premium.'
        )
        return redirect('subscription:my_subscription')
    
    # Récupérer les permissions temporaires actives
    temporary_permissions = UserTemporaryPermission.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('permission', 'subscription')
    
    # Vérifier si l'utilisateur a des permissions payantes actives
    has_paid_permissions = False
    if current_subscription and current_subscription.plan.price > 0:
        has_paid_permissions = temporary_permissions.filter(
            subscription__plan__price__gt=0
        ).exists()
    
    context = {
        'current_subscription': current_subscription,
        'temporary_permissions': temporary_permissions,
        'has_paid_permissions': has_paid_permissions,
        'user': request.user,
    }
    
    return render(request, 'subscription/test_permissions.html', context)