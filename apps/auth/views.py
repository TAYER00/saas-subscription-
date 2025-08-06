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
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm, CustomUserUpdateForm, PasswordResetRequestForm, PasswordResetConfirmForm
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
    
    def post(self, request, *args, **kwargs):
        """Gère la soumission du formulaire avec validation des deux formulaires."""
        self.object = self.get_object()
        user_form = self.get_form()
        profile_form = UserProfileForm(request.POST, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            # Sauvegarder les deux formulaires
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect(self.success_url)
        else:
            # Afficher les erreurs
            if not user_form.is_valid():
                messages.error(request, 'Erreur dans les informations utilisateur.')
            if not profile_form.is_valid():
                messages.error(request, 'Erreur dans les informations du profil.')
            return self.render_to_response(self.get_context_data(form=user_form, profile_form=profile_form))
    
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


@admin_required
def migrate_user_to_paid(request, user_id):
    """
    Migre un utilisateur d'un abonnement gratuit vers un abonnement payant.
    
    Cette vue permet aux administrateurs de :
    - Sélectionner un plan payant pour l'utilisateur
    - Créer un nouvel abonnement actif
    - Annuler l'ancien abonnement gratuit s'il existe
    - Enregistrer l'historique de la migration
    """
    from apps.subscription.models import Plan, Subscription, SubscriptionHistory
    from django.utils import timezone
    import json
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Utilisateur introuvable'
        })
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            plan_id = data.get('plan_id')
            
            if not plan_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Plan non spécifié'
                })
            
            # Récupérer le plan sélectionné
            try:
                new_plan = Plan.objects.get(id=plan_id, is_active=True)
            except Plan.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Plan introuvable ou inactif'
                })
            
            # Vérifier que ce n'est pas un plan gratuit
            if new_plan.plan_type == 'free':
                return JsonResponse({
                    'success': False,
                    'message': 'Impossible de migrer vers un plan gratuit'
                })
            
            # Vérifier si l'utilisateur a déjà un abonnement actif
            current_subscription = Subscription.objects.filter(
                user=user,
                status='active'
            ).first()
            
            # Vérifier si l'utilisateur a déjà un abonnement avec le nouveau plan (même inactif)
            existing_subscription_with_plan = Subscription.objects.filter(
                user=user,
                plan=new_plan
            ).first()
            
            old_plan = None
            if current_subscription:
                old_plan = current_subscription.plan
                # Annuler l'ancien abonnement
                current_subscription.status = 'cancelled'
                current_subscription.save()
            
            # Si l'utilisateur a déjà un abonnement avec ce plan, le réactiver
            if existing_subscription_with_plan:
                new_subscription = existing_subscription_with_plan
                new_subscription.status = 'active'
                new_subscription.start_date = timezone.now()
                new_subscription.amount_paid = new_plan.price
                new_subscription.payment_method = 'Migration administrative'
            else:
                # Créer un nouvel abonnement seulement s'il n'existe pas déjà
                new_subscription = Subscription.objects.create(
                    user=user,
                    plan=new_plan,
                    status='active',
                    start_date=timezone.now(),
                    amount_paid=new_plan.price,
                    payment_method='Migration administrative'
                )
            
            # Calculer la date de fin selon le cycle de facturation
            if new_plan.billing_cycle == 'monthly':
                new_subscription.end_date = new_subscription.start_date + timezone.timedelta(days=30)
                new_subscription.next_billing_date = new_subscription.end_date
            elif new_plan.billing_cycle == 'yearly':
                new_subscription.end_date = new_subscription.start_date + timezone.timedelta(days=365)
                new_subscription.next_billing_date = new_subscription.end_date
            elif new_plan.billing_cycle == 'lifetime':
                new_subscription.end_date = None
                new_subscription.next_billing_date = None
            
            new_subscription.save()
            
            # Enregistrer l'historique
            SubscriptionHistory.objects.create(
                subscription=new_subscription,
                action='upgraded' if old_plan and old_plan.price < new_plan.price else 'created',
                old_plan=old_plan,
                new_plan=new_plan,
                notes=f'Migration administrative par {request.user.email}'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Utilisateur migré vers le plan {new_plan.name} avec succès'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Données JSON invalides'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de la migration: {str(e)}'
            })
    
    # GET request - Retourner les plans disponibles
    available_plans = Plan.objects.filter(
        is_active=True,
        plan_type__in=['basic', 'premium', 'enterprise']
    ).order_by('price')
    
    plans_data = [{
        'id': plan.id,
        'name': plan.name,
        'price': float(plan.price),
        'billing_cycle': plan.get_billing_cycle_display(),
        'description': plan.description
    } for plan in available_plans]
    
    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'name': user.get_full_name() or user.email,
            'email': user.email
        },
        'available_plans': plans_data
    })


@admin_required
def migrate_user_to_free(request, user_id):
    """
    Migre un utilisateur d'un abonnement payant vers un abonnement gratuit.
    
    Cette vue permet aux administrateurs de :
    - Annuler l'abonnement payant actuel de l'utilisateur
    - Créer un nouvel abonnement gratuit
    - Enregistrer l'historique de la rétrogradation
    """
    from apps.subscription.models import Plan, Subscription, SubscriptionHistory
    from django.utils import timezone
    import json
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Utilisateur introuvable'
        })
    
    if request.method == 'POST':
        try:
            # Vérifier si l'utilisateur a un abonnement payant actif
            current_subscription = Subscription.objects.filter(
                user=user,
                status='active'
            ).first()
            
            if not current_subscription:
                return JsonResponse({
                    'success': False,
                    'message': 'Aucun abonnement actif trouvé pour cet utilisateur'
                })
            
            # Vérifier que l'abonnement actuel n'est pas déjà gratuit
            if current_subscription.plan.plan_type == 'free':
                return JsonResponse({
                    'success': False,
                    'message': 'L\'utilisateur a déjà un abonnement gratuit'
                })
            
            # Récupérer le plan gratuit
            try:
                free_plan = Plan.objects.get(plan_type='free', is_active=True)
            except Plan.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Plan gratuit introuvable'
                })
            
            old_plan = current_subscription.plan
            
            # Modifier l'abonnement existant au lieu de créer un nouveau (évite la contrainte unique)
            old_plan = current_subscription.plan
            
            # Passer au plan gratuit en modifiant l'abonnement existant
            current_subscription.plan = free_plan
            current_subscription.amount_paid = 0.00
            current_subscription.payment_method = 'Rétrogradation administrative'
            current_subscription.start_date = timezone.now()
            current_subscription.end_date = None
            current_subscription.next_billing_date = None
            current_subscription.save()
            
            new_subscription = current_subscription
            
            # Enregistrer l'historique
            SubscriptionHistory.objects.create(
                subscription=new_subscription,
                action='downgraded',
                old_plan=old_plan,
                new_plan=free_plan,
                notes=f'Rétrogradation administrative par {request.user.email}'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Utilisateur rétrogradé vers le plan gratuit avec succès'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de la rétrogradation: {str(e)}'
            })
    
    # GET request - Retourner les informations de l'utilisateur et son abonnement actuel
    current_subscription = Subscription.objects.filter(
        user=user,
        status='active'
    ).first()
    
    if not current_subscription or current_subscription.plan.plan_type == 'free':
        return JsonResponse({
            'success': False,
            'message': 'L\'utilisateur n\'a pas d\'abonnement payant actif'
        })
    
    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'name': user.get_full_name() or user.email,
            'email': user.email
        },
        'current_plan': {
            'name': current_subscription.plan.name,
            'price': float(current_subscription.plan.price),
            'billing_cycle': current_subscription.plan.get_billing_cycle_display()
        }
    })


# === GESTION DE LA RÉINITIALISATION DE MOT DE PASSE ===

def password_reset_request(request):
    """
    Vue pour demander une réinitialisation de mot de passe.
    Envoie un email avec un lien de réinitialisation.
    """
    from .forms import PasswordResetRequestForm
    from .models import PasswordResetToken
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse
    
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                
                # Créer un token de réinitialisation
                reset_token = PasswordResetToken.create_token(user)
                
                # Construire l'URL de réinitialisation
                reset_url = request.build_absolute_uri(
                    reverse('auth:password_reset_confirm', kwargs={'token': reset_token.token})
                )
                
                # Envoyer l'email
                subject = 'Réinitialisation de votre mot de passe'
                message = f"""
Bonjour {user.get_full_name() or user.email},

Vous avez demandé une réinitialisation de votre mot de passe.

Cliquez sur le lien suivant pour créer un nouveau mot de passe :
{reset_url}

Ce lien expirera dans 24 heures.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.

Cordialement,
L'équipe de support
"""
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                
                messages.success(
                    request,
                    'Un email de réinitialisation a été envoyé à votre adresse.'
                )
                return redirect('auth:login')
                
            except CustomUser.DoesNotExist:
                # Ne pas révéler si l'email existe ou non pour des raisons de sécurité
                messages.success(
                    request,
                    'Si cette adresse email existe, un email de réinitialisation a été envoyé.'
                )
                return redirect('auth:login')
            except Exception as e:
                messages.error(
                    request,
                    'Une erreur est survenue lors de l\'envoi de l\'email. Veuillez réessayer.'
                )
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'auth/password_reset_request.html', {'form': form})


def password_reset_confirm(request, token):
    """
    Vue pour confirmer la réinitialisation de mot de passe avec un token.
    """
    from .forms import PasswordResetConfirmForm
    from .models import PasswordResetToken
    
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
        
        if not reset_token.is_valid():
            messages.error(
                request,
                'Ce lien de réinitialisation a expiré ou a déjà été utilisé.'
            )
            return redirect('auth:password_reset_request')
        
        if request.method == 'POST':
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                # Mettre à jour le mot de passe
                user = reset_token.user
                user.set_password(form.cleaned_data['password1'])
                user.save()
                
                # Marquer le token comme utilisé
                reset_token.mark_as_used()
                
                messages.success(
                    request,
                    'Votre mot de passe a été réinitialisé avec succès. Vous pouvez maintenant vous connecter.'
                )
                return redirect('auth:login')
        else:
            form = PasswordResetConfirmForm()
        
        return render(request, 'auth/password_reset_confirm.html', {
            'form': form,
            'token': token,
            'user_email': reset_token.user.email
        })
        
    except PasswordResetToken.DoesNotExist:
        messages.error(
            request,
            'Lien de réinitialisation invalide.'
        )
        return redirect('auth:password_reset_request')