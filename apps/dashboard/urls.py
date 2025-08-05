from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard principal avec redirection automatique
    path('', views.DashboardView.as_view(), name='index'),
    
    # Redirection selon le rôle
    path('redirect/', views.dashboard_redirect, name='redirect'),
    
    # Dashboard spécifique admin
    path('admin/', views.AdminDashboardView.as_view(), name='admin'),
    
    # Dashboard spécifique client
    path('client/', views.ClientDashboardView.as_view(), name='client'),
    
    # APIs pour les données dynamiques
    path('api/quick-stats/', views.quick_stats_api, name='quick_stats_api'),
    path('api/activity-feed/', views.user_activity_feed, name='activity_feed_api'),
]