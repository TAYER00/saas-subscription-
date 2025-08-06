from django.urls import path
from . import views

app_name = 'auth'

urlpatterns = [
    # Authentification
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # Réinitialisation de mot de passe
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset-confirm/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    
    # Profil utilisateur
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    
    # Gestion des utilisateurs (admin uniquement)
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/change-type/', views.change_user_type, name='change_user_type'),
    
    # API
    path('api/user-info/', views.user_info_api, name='user_info_api'),
    
    # Migration d'abonnement (admin uniquement)
    path('users/<int:user_id>/migrate-to-paid/', views.migrate_user_to_paid, name='migrate_user_to_paid'),
    path('users/<int:user_id>/migrate-to-free/', views.migrate_user_to_free, name='migrate_user_to_free'),
    
    # Redirection
    path('dashboard-redirect/', views.dashboard_redirect, name='dashboard_redirect'),
]