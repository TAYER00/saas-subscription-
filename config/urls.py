from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.shortcuts import render


def custom_404_view(request, exception):
    """
    Vue personnalisée pour les erreurs 404.
    """
    context = {
        'error_type': '404',
        'error_title': 'Page non trouvée',
        'error_message': 'La page que vous recherchez n\'existe pas ou a été déplacée.',
        'error_suggestion': 'Vérifiez l\'URL ou retournez à la page d\'accueil.',
        'requested_url': request.path
    }
    return render(request, 'error.html', context, status=404)


def custom_405_view(request, exception):
    """
    Vue personnalisée pour les erreurs 405 (Method Not Allowed).
    """
    allowed_methods = getattr(exception, 'allowed_methods', [])
    context = {
        'error_type': '405',
        'error_title': 'Méthode non autorisée',
        'error_message': f'La méthode {request.method} n\'est pas autorisée pour cette URL.',
        'error_suggestion': f'Méthodes autorisées : {", ".join(allowed_methods) if allowed_methods else "Aucune"}',
        'requested_url': request.path,
        'requested_method': request.method
    }
    return render(request, 'error.html', context, status=405)


def custom_403_view(request, exception):
    """
    Vue personnalisée pour les erreurs 403 (Forbidden).
    """
    context = {
        'error_type': '403',
        'error_title': 'Accès interdit',
        'error_message': 'Vous n\'avez pas les permissions nécessaires pour accéder à cette page.',
        'error_suggestion': 'Connectez-vous avec un compte ayant les droits appropriés ou contactez l\'administrateur.',
        'requested_url': request.path
    }
    return render(request, 'error.html', context, status=403)


def custom_500_view(request):
    """
    Vue personnalisée pour les erreurs 500 (Internal Server Error).
    """
    context = {
        'error_type': '500',
        'error_title': 'Erreur interne du serveur',
        'error_message': 'Une erreur inattendue s\'est produite sur le serveur.',
        'error_suggestion': 'Veuillez réessayer dans quelques instants. Si le problème persiste, contactez l\'administrateur.',
        'requested_url': request.path if hasattr(request, 'path') else '/'
    }
    return render(request, 'error.html', context, status=500)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('apps.auth.urls')),
    path('subscription/', include('apps.subscription.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('tenders/', include('apps.tenders.urls')),
    path('', RedirectView.as_view(url='/dashboard/', permanent=False)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Gestionnaires d'erreurs personnalisés
handler404 = custom_404_view
handler405 = custom_405_view
handler403 = custom_403_view
handler500 = custom_500_view