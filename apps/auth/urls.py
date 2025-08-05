from django.urls import path
from . import views

app_name = 'auth'

urlpatterns = [
    # Authentification
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # Profil utilisateur
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    
    # Gestion des utilisateurs (admin uniquement)
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/change-type/', views.change_user_type, name='change_user_type'),
    
    # API
    path('api/user-info/', views.user_info_api, name='user_info_api'),
    
    # Redirection
    path('dashboard-redirect/', views.dashboard_redirect, name='dashboard_redirect'),
]