from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils import timezone
from .models import Tender, TenderSite, ScrapingLog
from datetime import datetime, timedelta
from .permissions import get_user_subscription_info, TenderViewPermissions
from apps.subscription.models import Subscription


@login_required
def tender_dashboard(request):
    """
    Vue principale du tableau de bord des appels d'offres.
    """
    # Filtres
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    site_filter = request.GET.get('site', '')
    category_filter = request.GET.get('category', '')
    
    # Requête de base
    tenders = Tender.objects.select_related('site').prefetch_related('documents')
    
    # Application des filtres
    if search_query:
        tenders = tenders.filter(
            Q(title__icontains=search_query) |
            Q(organization__icontains=search_query) |
            Q(reference__icontains=search_query)
        )
    
    if status_filter:
        tenders = tenders.filter(status=status_filter)
    
    if site_filter:
        tenders = tenders.filter(site_id=site_filter)
    
    if category_filter:
        tenders = tenders.filter(category=category_filter)
    
    # Tri
    sort_by = request.GET.get('sort', '-scraped_at')
    tenders = tenders.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(tenders, 20)  # 20 appels d'offres par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiques
    stats = {
        'total': Tender.objects.count(),
        'active': Tender.objects.filter(status='open').count(),
        'today': Tender.objects.filter(scraped_at__date=timezone.now().date()).count(),
        'this_week': Tender.objects.filter(scraped_at__gte=timezone.now() - timedelta(days=7)).count(),
    }
    
    # Données pour les filtres
    sites = TenderSite.objects.filter(is_active=True)
    status_choices = Tender.STATUS_CHOICES
    category_choices = Tender.CATEGORY_CHOICES
    
    # Informations d'abonnement de l'utilisateur
    user_subscription, is_premium = get_user_subscription_info(request.user)
    
    # Permissions d'affichage
    view_permissions = {
        'can_view_full_details': TenderViewPermissions.can_view_full_details(request.user),
        'can_use_advanced_filters': TenderViewPermissions.can_use_advanced_filters(request.user),
        'masked_fields': TenderViewPermissions.get_masked_fields_for_user(request.user)
    }
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'sites': sites,
        'status_choices': status_choices,
        'category_choices': category_choices,
        'current_filters': {
            'search': search_query,
            'status': status_filter,
            'site': site_filter,
            'category': category_filter,
            'sort': sort_by,
        },
        'user_subscription': user_subscription,
        'is_premium': is_premium,
        'view_permissions': view_permissions,
    }
    
    return render(request, 'tenders/tender_dashboard.html', context)


@login_required
def tender_detail(request, tender_id):
    """
    Vue détaillée d'un appel d'offres.
    """
    tender = get_object_or_404(Tender, id=tender_id)
    documents = tender.documents.all()
    
    # Informations d'abonnement de l'utilisateur
    user_subscription, is_premium = get_user_subscription_info(request.user)
    
    # Permissions d'affichage
    view_permissions = {
        'can_view_full_details': TenderViewPermissions.can_view_full_details(request.user),
        'can_download_documents': TenderViewPermissions.can_download_documents(request.user),
        'can_access_source_url': TenderViewPermissions.can_access_source_url(request.user),
        'masked_fields': TenderViewPermissions.get_masked_fields_for_user(request.user)
    }
    
    context = {
        'tender': tender,
        'documents': documents,
        'user_subscription': user_subscription,
        'is_premium': is_premium,
        'view_permissions': view_permissions,
    }
    
    return render(request, 'tenders/tender_detail.html', context)


@login_required
def scraping_logs(request):
    """
    Vue des logs de scraping.
    """
    logs = ScrapingLog.objects.select_related('site').order_by('-created_at')
    
    # Filtres
    site_filter = request.GET.get('site', '')
    status_filter = request.GET.get('status', '')
    
    if site_filter:
        logs = logs.filter(site_id=site_filter)
    
    if status_filter:
        logs = logs.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres
    sites = TenderSite.objects.all()
    status_choices = ScrapingLog.STATUS_CHOICES
    
    context = {
        'page_obj': page_obj,
        'sites': sites,
        'status_choices': status_choices,
        'current_filters': {
            'site': site_filter,
            'status': status_filter,
        }
    }
    
    return render(request, 'tenders/scraping_logs.html', context)


@login_required
def dashboard_stats_api(request):
    """
    API pour les statistiques du tableau de bord (AJAX).
    """
    # Statistiques par site
    sites_stats = TenderSite.objects.annotate(
        tender_count=Count('tenders')
    ).values('name', 'tender_count')
    
    # Statistiques par catégorie
    category_stats = Tender.objects.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Statistiques par statut
    status_stats = Tender.objects.values('status').annotate(
        count=Count('id')
    )
    
    # Évolution des appels d'offres (7 derniers jours)
    evolution_data = []
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        count = Tender.objects.filter(scraped_at__date=date).count()
        evolution_data.append({
            'date': date.strftime('%d/%m'),
            'count': count
        })
    
    data = {
        'sites_stats': list(sites_stats),
        'category_stats': list(category_stats),
        'status_stats': list(status_stats),
        'evolution_data': list(reversed(evolution_data))
    }
    
    return JsonResponse(data)
