# === IMPORTS DJANGO CORE ===
from django.shortcuts import render, redirect
# Fonctions d'authentification Django
from django.contrib.auth import login, logout, authenticate
# Décorateur pour protéger les vues
from django.contrib.auth.decorators import login_required
# Vues génériques d'authentification
from django.contrib.auth.views import LoginView, LogoutView
# Vues génériques basées sur les classes
from django.views.generic import CreateView, UpdateView, DetailView
# Mixin pour protéger les vues basées sur les classes
from django.contrib.auth.mixins import LoginRequiredMixin
# Système de messages Django
from django.contrib import messages
# URLs avec évaluation paresseuse
from django.urls import reverse_lazy
# Réponses JSON pour les API
from django.http import JsonResponse
# Décorateurs pour les méthodes HTTP
from django.views.decorators.http import require_http_methods
# Protection CSRF
from django.views.decorators.csrf import csrf_exempt
# Utilitaires pour les décorateurs
from django.utils.decorators import method_decorator

# === IMPORTS LOCAUX ===
# Nos modèles personnalisés
from .models import CustomUser, UserProfile
# Nos formulaires personnalisés
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm, CustomUserUpdateForm
# Nos permissions personnalisées
from .permissions import admin_required, AdminRequiredMixin


class CustomLoginView(LoginView):
    """
    Vue de connexion personnalisée utilisant notre formulaire d'authentification.
    
    Fonctionnalités :
    - Utilise CustomAuthenticationForm (authentification par email)
    - Redirige les utilisateurs déjà connectés
    - Affiche des messages de succès/erreur
    - Redirige vers le dashboard après connexion
    
    Hérite de :
        LoginView : Vue générique Django pour la connexion
    """
    # Utilise notre formulaire personnalisé (email au lieu de username)
    form_class = CustomAuthenticationForm
    # Template de la page de connexion
    template_name = 'auth/login.html'
    # Redirige automatiquement les utilisateurs déjà connectés
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """
        Détermine l'URL de redirection après connexion réussie.
        
        Returns:
            str: URL vers le dashboard
        """
        return reverse_lazy('dashboard:index')
    
    def form_valid(self, form):
        """
        Traite un formulaire valide (connexion réussie).
        
        Args:
            form: Formulaire d'authentification validé
            
        Returns:
            HttpResponse: Redirection vers la page de succès
        """
        # Message de bienvenue personnalisé
        messages.success(self.request, f'Bienvenue {form.get_user().get_full_name()}!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """
        Traite un formulaire invalide (échec de connexion).
        
        Args:
            form: Formulaire d'authentification avec erreurs
            
        Returns:
            HttpResponse: Retour au formulaire avec erreurs
        """
        # Message d'erreur générique pour la sécurité
        messages.error(self.request, 'Email ou mot de passe incorrect.')
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    """
    Vue de déconnexion personnalisée avec message informatif.
    
    Fonctionnalités :
    - Déconnecte l'utilisateur
    - Affiche un message de confirmation
    - Redirige vers la page de connexion
    
    Hérite de :
        LogoutView : Vue générique Django pour la déconnexion
    """
    # Page de redirection après déconnexion
    next_page = reverse_lazy('auth:login')
    
    def dispatch(self, request, *args, **kwargs):
        """
        Traite la requête de déconnexion.
        
        Args:
            request: Requête HTTP
            *args, **kwargs: Arguments additionnels
            
        Returns:
            HttpResponse: Redirection après déconnexion
        """
        # Message informatif avant la déconnexion
        messages.info(request, 'Vous avez été déconnecté avec succès.')
        return super().dispatch(request, *args, **kwargs)


class RegisterView(CreateView):
    """
    Vue d'inscription pour créer de nouveaux comptes utilisateur.
    
    Fonctionnalités :
    - Utilise CustomUserCreationForm
    - Crée automatiquement un UserProfile associé (via signal)
    - Affiche des messages de succès/erreur
    - Redirige vers la page de connexion après inscription
    
    Hérite de :
        CreateView : Vue générique Django pour créer des objets
    """
    # Modèle à créer
    model = CustomUser
    # Formulaire d'inscription personnalisé
    form_class = CustomUserCreationForm
    # Template de la page d'inscription
    template_name = 'auth/register.html'
    # Redirection après inscription réussie
    success_url = reverse_lazy('auth:login')
    
    def form_valid(self, form):
        """
        Traite un formulaire valide (inscription réussie).
        
        Args:
            form: Formulaire d'inscription validé
            
        Returns:
            HttpResponse: Redirection vers la page de succès
        """
        # Sauvegarde de l'utilisateur
        response = super().form_valid(form)
        # Message de confirmation
        messages.success(
            self.request,
            f'Compte créé avec succès pour {form.cleaned_data["email"]}. Vous pouvez maintenant vous connecter.'
        )
        return response
    
    def form_invalid(self, form):
        """
        Traite un formulaire invalide (erreur d'inscription).
        
        Args:
            form: Formulaire d'inscription avec erreurs
            
        Returns:
            HttpResponse: Retour au formulaire avec erreurs
        """
        # Message d'erreur générique
        messages.error(self.request, 'Erreur lors de la création du compte. Veuillez vérifier les informations saisies.')
        return super().form_invalid(form)


class ProfileView(LoginRequiredMixin, DetailView):
    """
    Vue pour afficher le profil de l'utilisateur connecté.
    
    Fonctionnalités :
    - Affiche les informations de l'utilisateur et son profil
    - Accessible uniquement aux utilisateurs connectés
    - Fournit les formulaires de modification en contexte
    
    Hérite de :
        LoginRequiredMixin : Requiert une authentification
        DetailView : Vue générique pour afficher un objet
    """
    # Modèle à afficher
    model = CustomUser
    # Template de la page de profil
    template_name = 'auth/profile.html'
    # Nom de la variable dans le template
    context_object_name = 'profile_user'
    
    def get_object(self):
        """
        Retourne l'utilisateur à afficher (toujours l'utilisateur connecté).
        
        Returns:
            CustomUser: L'utilisateur connecté
        """
        return self.request.user
    
    def get_context_data(self, **kwargs):
        """
        Ajoute les formulaires de modification au contexte.
        
        Args:
            **kwargs: Arguments du contexte parent
            
        Returns:
            dict: Contexte enrichi avec les formulaires
        """
        context = super().get_context_data(**kwargs)
        # Formulaire pour modifier les infos utilisateur
        context['user_form'] = CustomUserUpdateForm(instance=self.request.user)
        # Formulaire pour modifier le profil
        context['profile_form'] = UserProfileForm(instance=self.request.user.profile)
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Vue pour modifier le profil utilisateur."""
    model = CustomUser
    form_class = CustomUserUpdateForm
    template_name = 'auth/profile_edit.html'
    success_url = reverse_lazy('auth:profile')
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['profile_form'] = UserProfileForm(self.request.POST, instance=self.request.user.profile)
        else:
            context['profile_form'] = UserProfileForm(instance=self.request.user.profile)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        profile_form = context['profile_form']
        
        if profile_form.is_valid():
            self.object = form.save()
            profile_form.instance = self.object.profile
            profile_form.save()
            messages.success(self.request, 'Profil mis à jour avec succès!')
            return redirect(self.success_url)
        else:
            return self.render_to_response(self.get_context_data(form=form))
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erreur lors de la mise à jour du profil.')
        return super().form_invalid(form)


class UserListView(AdminRequiredMixin, LoginRequiredMixin, DetailView):
    """Vue pour lister tous les utilisateurs (admin uniquement)."""
    template_name = 'auth/user_list.html'
    
    def get(self, request, *args, **kwargs):
        users = CustomUser.objects.all().select_related('profile').prefetch_related('groups')
        context = {
            'users': users,
            'total_users': users.count(),
            'admin_users': users.filter(user_type='admin').count(),
            'client_users': users.filter(user_type='client').count(),
        }
        return render(request, self.template_name, context)


@admin_required
def toggle_user_status(request, user_id):
    """Vue pour activer/désactiver un utilisateur (admin uniquement)."""
    try:
        user = CustomUser.objects.get(id=user_id)
        user.is_active = not user.is_active
        user.save()
        
        status = 'activé' if user.is_active else 'désactivé'
        messages.success(request, f'Utilisateur {user.email} {status} avec succès.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Utilisateur {status}',
                'is_active': user.is_active
            })
    except CustomUser.DoesNotExist:
        messages.error(request, 'Utilisateur introuvable.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Utilisateur introuvable'})
    
    return redirect('auth:user_list')


@admin_required
def change_user_type(request, user_id):
    """Vue pour changer le type d'utilisateur (admin uniquement)."""
    if request.method == 'POST':
        try:
            user = CustomUser.objects.get(id=user_id)
            new_type = request.POST.get('user_type')
            
            if new_type in ['admin', 'client']:
                old_type = user.user_type
                user.user_type = new_type
                user.save()
                
                # Mettre à jour les groupes
                user.groups.clear()
                if new_type == 'admin':
                    from django.contrib.auth.models import Group
                    admin_group, _ = Group.objects.get_or_create(name='admin')
                    user.groups.add(admin_group)
                elif new_type == 'client':
                    from django.contrib.auth.models import Group
                    client_group, _ = Group.objects.get_or_create(name='client')
                    user.groups.add(client_group)
                
                messages.success(request, f'Type d\'utilisateur changé de {old_type} à {new_type} pour {user.email}.')
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Type changé à {new_type}',
                        'user_type': new_type
                    })
            else:
                messages.error(request, 'Type d\'utilisateur invalide.')
                
        except CustomUser.DoesNotExist:
            messages.error(request, 'Utilisateur introuvable.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Utilisateur introuvable'})
    
    return redirect('auth:user_list')


@login_required
def dashboard_redirect(request):
    """Redirige vers le dashboard approprié selon le type d'utilisateur."""
    if request.user.is_admin:
        return redirect('dashboard:admin')
    else:
        return redirect('dashboard:client')


@require_http_methods(["GET"])
@login_required
def user_info_api(request):
    """API pour obtenir les informations de l'utilisateur connecté."""
    user = request.user
    data = {
        'id': user.id,
        'email': user.email,
        'full_name': user.get_full_name(),
        'user_type': user.user_type,
        'is_admin': user.is_admin,
        'is_client': user.is_client,
        'groups': [group.name for group in user.groups.all()],
        'permissions': list(user.get_all_permissions()),
        'is_active': user.is_active,
        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
    }
    return JsonResponse(data)