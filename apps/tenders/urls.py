from django.urls import path
from . import views

app_name = 'tenders'

urlpatterns = [
    path('', views.tender_dashboard, name='dashboard'),
    path('tender/<int:tender_id>/', views.tender_detail, name='detail'),
    path('logs/', views.scraping_logs, name='logs'),
    path('api/stats/', views.dashboard_stats_api, name='stats_api'),
]