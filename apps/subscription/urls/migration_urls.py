from django.urls import path
from ..views.migration_views import (
    migrate_to_paid_plan,
    renew_subscription,
    subscription_detail,
    admin_migration_dashboard,
    admin_migrate_user,
    cleanup_expired_permissions,
    UserPermissionListView,
    MigrationLogListView
)

# URLs pour la gestion des migrations d'abonnements
app_name = 'migration'

urlpatterns = [
    # URLs pour les utilisateurs
    path('select-plan/', migrate_to_paid_plan, name='select_plan'),
    path('subscription/', subscription_detail, name='subscription_detail'),
    path('renew/', renew_subscription, name='renew_subscription'),
    
    # URLs pour l'administration
    path('admin/dashboard/', admin_migration_dashboard, name='admin_dashboard'),
    path('admin/migrate-user/', admin_migrate_user, name='admin_migrate_user'),
    path('admin/cleanup/', cleanup_expired_permissions, name='cleanup_expired_permissions'),
    path('admin/permissions/', UserPermissionListView.as_view(), name='user_permissions'),
    path('admin/logs/', MigrationLogListView.as_view(), name='migration_logs'),
]