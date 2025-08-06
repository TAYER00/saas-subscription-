# -*- coding: utf-8 -*-
"""
Vues pour la gestion des migrations d'abonnements.

Ce module contient les vues pour :
- Migrer un utilisateur vers un plan payant
- Renouveler un abonnement
- Gérer les permissions temporaires
- Interface d'administration des migrations
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
import json
import logging

from ..models import Plan, Subscription
from ..models_permissions import UserTemporaryPermission, PermissionMigrationLog
from ..services import SubscriptionMigrationService
from apps.auth.models import CustomUser
from apps.auth.permissions import admin_required

# Configuration du logger
logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET", "POST"])
def migrate_to_paid_plan(request):
    """
    Vue pour migrer un utilisateur vers un plan payant.
    
    GET: Affiche le formulaire de sélection de plan
    POST: Traite la migration
    """
    if request.method == 'GET':
        # Récupérer les plans payants disponibles
        paid_plans = Plan.objects.filter(
            is_active=True,
            is_free=False
        ).order_by('price')
        
        # Récupérer l'abonnement actuel de l'utilisateur
        current_subscription = Subscription.objects.filter(
            user=request.user,
            is_active=True
        ).first()
        
        context = {
            'paid_plans': paid_plans,
            'current_subscription': current_subscription,
            'user': request.user
        }
        
        return render(request, 'subscription/migration/select_plan.html', context)
    
    elif request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            plan_id = request.POST.get('plan_id')
            duration_days = int(request.POST.get('duration_days', 30))
            
            if not plan_id:
                messages.error(request, "Veuillez sélectionner un plan.")
                return redirect('subscription:migrate_to_paid_plan')
            
            # Récupérer le plan sélectionné
            plan = get_object_or_404(Plan, id=plan_id, is_active=True, is_free=False)
            
            # Effectuer la migration
            result = SubscriptionMigrationService.migrate_user_to_paid_plan(
                user=request.user,
                new_plan=plan,
                duration_days=duration_days,
                auto_activate=True
            )
            
            if result['success']:
                messages.success(
                    request, 
                    f"Migration réussie vers le plan {plan.name}! "
                    f"Vous avez maintenant accès aux fonctionnalités premium."
                )
                return redirect('subscription:subscription_detail')
            else:
                messages.error(request, "Erreur lors de la migration.")
                
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Erreur lors de la migration pour {request.user.email}: {str(e)}")
            messages.error(request, "Une erreur inattendue s'est produite.")
        
        return redirect('subscription:migrate_to_paid_plan')


@login_required
@require_POST
def renew_subscription(request):
    """
    Vue pour renouveler l'abonnement d'un utilisateur.
    
    POST: Traite le renouvellement via AJAX
    """
    try:
        # Récupérer les données JSON
        data = json.loads(request.body)
        duration_days = data.get('duration_days', 30)
        extend_existing = data.get('extend_existing', True)
        
        # Effectuer le renouvellement
        result = SubscriptionMigrationService.renew_subscription(
            user=request.user,
            duration_days=duration_days,
            extend_existing=extend_existing
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result['message'],
                'subscription': {
                    'id': result['subscription'].id,
                    'plan_name': result['subscription'].plan.name,
                    'end_date': result['subscription'].end_date.isoformat(),
                    'is_active': result['subscription'].is_active
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Erreur lors du renouvellement'
            })
            
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        logger.error(f"Erreur lors du renouvellement pour {request.user.email}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Une erreur inattendue s\'est produite'
        })


@login_required
def subscription_detail(request):
    """
    Vue détaillée de l'abonnement de l'utilisateur.
    
    Affiche l'abonnement actuel, les permissions temporaires,
    et les options de renouvellement.
    """
    # Récupérer l'abonnement actuel
    current_subscription = Subscription.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('plan').first()
    
    # Récupérer les permissions temporaires actives
    active_permissions = UserTemporaryPermission.objects.filter(
        user=request.user,
        is_active=True,
        expires_at__gt=timezone.now()
    ).select_related('permission').order_by('expires_at')
    
    # Récupérer les permissions expirées récemment (7 derniers jours)
    recent_expired = UserTemporaryPermission.objects.filter(
        user=request.user,
        is_active=False,
        expires_at__gte=timezone.now() - timedelta(days=7)
    ).select_related('permission').order_by('-expires_at')
    
    # Récupérer les plans disponibles pour migration
    available_plans = Plan.objects.filter(
        is_active=True,
        is_free=False
    ).exclude(
        id=current_subscription.plan.id if current_subscription else None
    ).order_by('price')
    
    context = {
        'current_subscription': current_subscription,
        'active_permissions': active_permissions,
        'recent_expired': recent_expired,
        'available_plans': available_plans,
        'can_renew': current_subscription and not current_subscription.plan.is_free
    }
    
    return render(request, 'subscription/migration/subscription_detail.html', context)


@admin_required
def admin_migration_dashboard(request):
    """
    Tableau de bord d'administration des migrations.
    
    Vue réservée aux administrateurs pour surveiller
    les migrations et permissions temporaires.
    """
    # Statistiques générales
    total_paid_subscriptions = Subscription.objects.filter(
        is_active=True,
        plan__is_free=False
    ).count()
    
    active_temp_permissions = UserTemporaryPermission.objects.filter(
        is_active=True,
        expires_at__gt=timezone.now()
    ).count()
    
    expired_today = UserTemporaryPermission.objects.filter(
        expires_at__date=timezone.now().date(),
        is_active=False
    ).count()
    
    # Migrations récentes (7 derniers jours)
    recent_migrations = PermissionMigrationLog.objects.filter(
        action='MIGRATE',
        timestamp__gte=timezone.now() - timedelta(days=7)
    ).select_related('user', 'old_plan', 'new_plan').order_by('-timestamp')[:10]
    
    # Permissions expirant bientôt (3 prochains jours)
    expiring_soon = UserTemporaryPermission.objects.filter(
        is_active=True,
        expires_at__lte=timezone.now() + timedelta(days=3),
        expires_at__gt=timezone.now()
    ).select_related('user', 'permission').order_by('expires_at')[:10]
    
    context = {
        'stats': {
            'total_paid_subscriptions': total_paid_subscriptions,
            'active_temp_permissions': active_temp_permissions,
            'expired_today': expired_today
        },
        'recent_migrations': recent_migrations,
        'expiring_soon': expiring_soon
    }
    
    return render(request, 'subscription/admin/migration_dashboard.html', context)


@admin_required
@require_POST
def admin_migrate_user(request):
    """
    Vue d'administration pour migrer un utilisateur.
    
    Permet aux administrateurs de migrer n'importe quel utilisateur
    vers un plan payant.
    """
    try:
        # Récupérer les données du formulaire
        user_id = request.POST.get('user_id')
        plan_id = request.POST.get('plan_id')
        duration_days = int(request.POST.get('duration_days', 30))
        
        if not user_id or not plan_id:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur et plan requis'
            })
        
        # Récupérer l'utilisateur et le plan
        user = get_object_or_404(CustomUser, id=user_id)
        plan = get_object_or_404(Plan, id=plan_id, is_active=True, is_free=False)
        
        # Effectuer la migration
        result = SubscriptionMigrationService.migrate_user_to_paid_plan(
            user=user,
            new_plan=plan,
            duration_days=duration_days,
            auto_activate=True
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': f'Migration de {user.email} vers {plan.name} réussie',
                'subscription_id': result['subscription'].id
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Erreur lors de la migration'
            })
            
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        logger.error(f"Erreur lors de la migration admin: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Une erreur inattendue s\'est produite'
        })


@admin_required
@require_POST
def cleanup_expired_permissions(request):
    """
    Vue d'administration pour nettoyer les permissions expirées.
    
    Déclenche manuellement le nettoyage des permissions expirées.
    """
    try:
        result = SubscriptionMigrationService.cleanup_expired_permissions()
        
        return JsonResponse({
            'success': True,
            'message': result['message'],
            'expired_count': result['expired_permissions']
        })
        
    except Exception as e:
        logger.error(f"Erreur lors du nettoyage: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Erreur lors du nettoyage des permissions'
        })


@method_decorator(admin_required, name='dispatch')
class UserPermissionListView(ListView):
    """
    Vue liste des permissions temporaires des utilisateurs.
    
    Vue d'administration pour surveiller toutes les permissions
    temporaires du système.
    """
    model = UserTemporaryPermission
    template_name = 'subscription/admin/user_permissions_list.html'
    context_object_name = 'permissions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = UserTemporaryPermission.objects.select_related(
            'user', 'permission', 'subscription__plan'
        ).order_by('-granted_at')
        
        # Filtres
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(
                is_active=True,
                expires_at__gt=timezone.now()
            )
        elif status == 'expired':
            queryset = queryset.filter(
                Q(is_active=False) | Q(expires_at__lte=timezone.now())
            )
        
        user_search = self.request.GET.get('user')
        if user_search:
            queryset = queryset.filter(
                Q(user__email__icontains=user_search) |
                Q(user__first_name__icontains=user_search) |
                Q(user__last_name__icontains=user_search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', '')
        context['user_search'] = self.request.GET.get('user', '')
        return context


@method_decorator(admin_required, name='dispatch')
class MigrationLogListView(ListView):
    """
    Vue liste des journaux de migration.
    
    Vue d'administration pour consulter l'historique
    des migrations et actions sur les permissions.
    """
    model = PermissionMigrationLog
    template_name = 'subscription/admin/migration_logs.html'
    context_object_name = 'logs'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = PermissionMigrationLog.objects.select_related(
            'user', 'permission', 'old_plan', 'new_plan', 'subscription'
        ).order_by('-timestamp')
        
        # Filtres
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        user_search = self.request.GET.get('user')
        if user_search:
            queryset = queryset.filter(
                Q(user__email__icontains=user_search) |
                Q(user__first_name__icontains=user_search) |
                Q(user__last_name__icontains=user_search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_choices'] = PermissionMigrationLog.ACTION_CHOICES
        context['action_filter'] = self.request.GET.get('action', '')
        context['user_search'] = self.request.GET.get('user', '')
        return context