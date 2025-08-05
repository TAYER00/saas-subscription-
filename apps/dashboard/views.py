from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from apps.auth.models import CustomUser
from apps.subscription.models import Plan, Subscription
from apps.auth.permissions import AdminRequiredMixin, ClientRequiredMixin, get_user_role_context


class DashboardView(LoginRequiredMixin, TemplateView):
    """Vue principale du dashboard avec affichage conditionnel selon le rôle."""
    template_name = 'dashboard/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Ajouter le contexte des rôles
        context.update(get_user_role_context(user))
        
        # Données spécifiques selon le rôle
        if user.is_admin:
            context.update(self.get_admin_context())
        else:
            context.update(self.get_client_context())
        
        return context
    
    def get_admin_context(self):
        """Contexte spécifique pour les administrateurs."""
        # Statistiques générales
        total_users = CustomUser.objects.count()
        total_subscriptions = Subscription.objects.filter(status='active').count()
        total_revenue = Subscription.objects.filter(
            status='active'
        ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        
        # Statistiques par plan
        plan_stats = Plan.objects.annotate(
            subscription_count=Count('subscriptions', filter=Q(subscriptions__status='active'))
        ).order_by('-subscription_count')
        
        # Nouveaux utilisateurs cette semaine
        week_ago = timezone.now() - timedelta(days=7)
        new_users_week = CustomUser.objects.filter(date_joined__gte=week_ago).count()
        
        # Abonnements récents
        recent_subscriptions = Subscription.objects.select_related(
            'user', 'plan'
        ).filter(
            status='active'
        ).order_by('-created_at')[:5]
        
        return {
            'dashboard_type': 'admin',
            'total_users': total_users,
            'total_subscriptions': total_subscriptions,
            'total_revenue': total_revenue,
            'new_users_week': new_users_week,
            'plan_stats': plan_stats,
            'recent_subscriptions': recent_subscriptions,
        }
    
    def get_client_context(self):
        """Contexte spécifique pour les clients."""
        user = self.request.user
        
        # Abonnement actuel
        current_subscription = Subscription.objects.filter(
            user=user,
            status='active'
        ).first()
        
        # Historique des abonnements
        subscription_history = Subscription.objects.filter(
            user=user
        ).select_related('plan').order_by('-created_at')[:5]
        
        # Plans disponibles pour mise à niveau
        available_plans = Plan.objects.filter(is_active=True)
        if current_subscription:
            available_plans = available_plans.exclude(id=current_subscription.plan.id)
        
        return {
            'dashboard_type': 'client',
            'current_subscription': current_subscription,
            'subscription_history': subscription_history,
            'available_plans': available_plans[:3],  # Limiter à 3 plans
        }


class AdminDashboardView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    """Dashboard spécifique aux administrateurs."""
    template_name = 'dashboard/admin.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiques détaillées
        context['stats'] = self.get_detailed_stats()
        context['charts_data'] = self.get_charts_data()
        
        return context
    
    def get_detailed_stats(self):
        """Statistiques détaillées pour les admins."""
        from django.db.models import Q
        
        now = timezone.now()
        month_ago = now - timedelta(days=30)
        
        return {
            'users': {
                'total': CustomUser.objects.count(),
                'admins': CustomUser.objects.filter(user_type='admin').count(),
                'clients': CustomUser.objects.filter(user_type='client').count(),
                'active': CustomUser.objects.filter(is_active=True).count(),
                'new_this_month': CustomUser.objects.filter(date_joined__gte=month_ago).count(),
            },
            'subscriptions': {
                'total': Subscription.objects.count(),
                'active': Subscription.objects.filter(status='active').count(),
                'cancelled': Subscription.objects.filter(status='cancelled').count(),
                'expired': Subscription.objects.filter(status='expired').count(),
                'new_this_month': Subscription.objects.filter(created_at__gte=month_ago).count(),
            },
            'revenue': {
                'total': Subscription.objects.filter(
                    status='active'
                ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0,
                'this_month': Subscription.objects.filter(
                    created_at__gte=month_ago,
                    status='active'
                ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0,
            },
            'plans': {
                'total': Plan.objects.count(),
                'active': Plan.objects.filter(is_active=True).count(),
                'most_popular': Plan.objects.annotate(
                    sub_count=Count('subscriptions', filter=Q(subscriptions__status='active'))
                ).order_by('-sub_count').first(),
            }
        }
    
    def get_charts_data(self):
        """Données pour les graphiques."""
        # Données pour le graphique des inscriptions par jour (7 derniers jours)
        days_data = []
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            count = CustomUser.objects.filter(date_joined__date=date).count()
            days_data.append({
                'date': date.strftime('%d/%m'),
                'count': count
            })
        
        # Répartition des abonnements par plan
        plan_data = []
        for plan in Plan.objects.all():
            count = plan.subscriptions.filter(status='active').count()
            if count > 0:
                plan_data.append({
                    'name': plan.name,
                    'count': count,
                    'revenue': float(count * plan.price)
                })
        
        return {
            'registrations': list(reversed(days_data)),
            'plans': plan_data,
        }


class ClientDashboardView(ClientRequiredMixin, LoginRequiredMixin, TemplateView):
    """Dashboard spécifique aux clients."""
    template_name = 'dashboard/client.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Informations sur l'abonnement
        current_subscription = Subscription.objects.filter(
            user=user,
            status='active'
        ).first()
        
        context.update({
            'current_subscription': current_subscription,
            'usage_stats': self.get_usage_stats(user, current_subscription),
            'recommendations': self.get_recommendations(user, current_subscription),
        })
        
        return context
    
    def get_usage_stats(self, user, subscription):
        """Statistiques d'utilisation pour le client."""
        if not subscription:
            return None
        
        plan = subscription.plan
        
        # Simuler des statistiques d'utilisation
        # Dans un vrai projet, ces données viendraient de l'utilisation réelle
        return {
            'users': {
                'used': 1,  # L'utilisateur actuel
                'limit': plan.max_users,
                'percentage': (1 / plan.max_users * 100) if plan.max_users > 0 else 0
            },
            'projects': {
                'used': 0,  # À implémenter selon votre logique métier
                'limit': plan.max_projects,
                'percentage': 0
            },
            'storage': {
                'used': 0.1,  # GB utilisés
                'limit': plan.storage_limit_gb,
                'percentage': (0.1 / plan.storage_limit_gb * 100) if plan.storage_limit_gb > 0 else 0
            }
        }
    
    def get_recommendations(self, user, subscription):
        """Recommandations pour le client."""
        recommendations = []
        
        if not subscription:
            recommendations.append({
                'type': 'warning',
                'title': 'Aucun abonnement actif',
                'message': 'Souscrivez à un plan pour accéder à toutes les fonctionnalités.',
                'action': 'Voir les plans',
                'url': '/subscription/plans/'
            })
        else:
            # Vérifier si l'abonnement expire bientôt
            if subscription.days_remaining and subscription.days_remaining <= 7:
                recommendations.append({
                    'type': 'warning',
                    'title': 'Abonnement expire bientôt',
                    'message': f'Votre abonnement expire dans {subscription.days_remaining} jour(s).',
                    'action': 'Renouveler',
                    'url': '/subscription/renew/'
                })
            
            # Recommander une mise à niveau si plan basique
            if subscription.plan.plan_type == 'free':
                recommendations.append({
                    'type': 'info',
                    'title': 'Découvrez nos plans premium',
                    'message': 'Accédez à plus de fonctionnalités avec nos plans payants.',
                    'action': 'Voir les plans',
                    'url': '/subscription/plans/'
                })
        
        return recommendations


@login_required
def dashboard_redirect(request):
    """Redirige vers le bon dashboard selon le rôle."""
    if request.user.is_admin:
        return redirect('dashboard:admin')
    else:
        return redirect('dashboard:client')


@login_required
def quick_stats_api(request):
    """API pour les statistiques rapides (utilisée par AJAX)."""
    user = request.user
    
    if user.is_admin:
        data = {
            'total_users': CustomUser.objects.count(),
            'active_subscriptions': Subscription.objects.filter(status='active').count(),
            'total_revenue': float(
                Subscription.objects.filter(
                    status='active'
                ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
            ),
            'new_users_today': CustomUser.objects.filter(
                date_joined__date=timezone.now().date()
            ).count(),
        }
    else:
        subscription = Subscription.objects.filter(
            user=user,
            status='active'
        ).first()
        
        data = {
            'has_subscription': bool(subscription),
            'plan_name': subscription.plan.name if subscription else None,
            'days_remaining': subscription.days_remaining if subscription else None,
            'subscription_status': subscription.status if subscription else None,
        }
    
    return JsonResponse(data)


@login_required
def user_activity_feed(request):
    """Feed d'activité pour l'utilisateur."""
    user = request.user
    activities = []
    
    if user.is_admin:
        # Activités récentes pour les admins
        recent_users = CustomUser.objects.order_by('-date_joined')[:5]
        for u in recent_users:
            activities.append({
                'type': 'user_registered',
                'message': f'Nouvel utilisateur: {u.get_full_name()} ({u.email})',
                'timestamp': u.date_joined,
                'icon': 'user-plus'
            })
        
        recent_subscriptions = Subscription.objects.select_related(
            'user', 'plan'
        ).order_by('-created_at')[:5]
        for sub in recent_subscriptions:
            activities.append({
                'type': 'subscription_created',
                'message': f'{sub.user.get_full_name()} s\'est abonné au plan {sub.plan.name}',
                'timestamp': sub.created_at,
                'icon': 'credit-card'
            })
    else:
        # Activités pour les clients
        user_subscriptions = Subscription.objects.filter(
            user=user
        ).select_related('plan').order_by('-created_at')[:10]
        
        for sub in user_subscriptions:
            activities.append({
                'type': 'subscription_activity',
                'message': f'Abonnement au plan {sub.plan.name} - {sub.get_status_display()}',
                'timestamp': sub.created_at,
                'icon': 'calendar'
            })
    
    # Trier par timestamp
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return JsonResponse({'activities': activities[:10]})