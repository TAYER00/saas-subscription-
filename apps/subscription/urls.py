from django.urls import path
from . import views

app_name = 'subscription'

urlpatterns = [
    # Plans publics
    path('plans/', views.PlanListView.as_view(), name='plans'),
    path('plans/<slug:slug>/', views.PlanDetailView.as_view(), name='plan_detail'),
    
    # Gestion des abonnements
    path('subscribe/<int:plan_id>/', views.subscribe_to_plan, name='subscribe'),
    path('change-plan/<int:plan_id>/', views.change_plan, name='change_plan'),
    path('my-subscription/', views.my_subscription, name='my_subscription'),
    path('cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('renew/', views.renew_subscription, name='renew_subscription'),
    
    # Administration
    path('admin/subscriptions/', views.AdminSubscriptionListView.as_view(), name='admin_subscriptions'),
    path('admin/plans/', views.AdminPlanListView.as_view(), name='admin_plans'),
    path('admin/plans/<int:plan_id>/toggle/', views.toggle_plan_status, name='toggle_plan_status'),
    
    # API
    path('api/subscription-info/', views.subscription_api, name='subscription_api'),
]