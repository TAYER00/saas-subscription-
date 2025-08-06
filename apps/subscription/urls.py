from django.urls import path, include
from . import views as main_views
from .view_modules.migration_views import (
    migrate_to_paid_plan,
    renew_subscription as renew_subscription_migration,
    subscription_detail,
    admin_migration_dashboard,
    admin_migrate_user,
    cleanup_expired_permissions,
    UserPermissionListView,
    MigrationLogListView
)

app_name = 'subscription'

urlpatterns = [
    # Plans publics
    path('plans/', main_views.PlanListView.as_view(), name='plans'),
    path('plans/<slug:slug>/', main_views.PlanDetailView.as_view(), name='plan_detail'),
    
    # Gestion des abonnements (existant)
    path('subscribe/<int:plan_id>/', main_views.subscribe_to_plan, name='subscribe'),
    path('payment/<int:plan_id>/', main_views.payment_page, name='payment'),
    path('change-plan/<int:plan_id>/', main_views.change_plan, name='change_plan'),
    path('my-subscription/', main_views.my_subscription, name='my_subscription'),
    path('cancel/', main_views.cancel_subscription, name='cancel_subscription'),
    path('renew/', main_views.renew_subscription, name='renew_subscription'),
    
    # Migration et permissions temporaires (nouveau module)
    path('migrate/select-plan/', migrate_to_paid_plan, name='select_plan'),
    path('migrate/subscription/', subscription_detail, name='subscription_detail'),
    path('migrate/renew/', renew_subscription_migration, name='renew_subscription_migration'),
    
    # Administration
    path('admin/subscriptions/', main_views.AdminSubscriptionListView.as_view(), name='admin_subscriptions'),
    path('admin/plans/', main_views.AdminPlanListView.as_view(), name='admin_plans'),
    path('admin/plans/<int:plan_id>/toggle/', main_views.toggle_plan_status, name='toggle_plan_status'),
    
    # Administration des migrations
    path('admin/migration/dashboard/', admin_migration_dashboard, name='admin_migration_dashboard'),
    path('admin/migration/migrate-user/', admin_migrate_user, name='admin_migrate_user'),
    path('admin/migration/cleanup/', cleanup_expired_permissions, name='cleanup_expired_permissions'),
    path('admin/migration/permissions/', UserPermissionListView.as_view(), name='user_permissions'),
    path('admin/migration/logs/', MigrationLogListView.as_view(), name='migration_logs'),
    
    # API
    path('api/subscription-info/', main_views.subscription_api, name='subscription_api'),
    
    # Page de test des permissions
    path('test-permissions/', main_views.test_permissions, name='test_permissions'),
]