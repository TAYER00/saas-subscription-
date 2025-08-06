from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from .models import CustomUser, UserProfile


class UserProfileInline(admin.StackedInline):
    """Inline pour le profil utilisateur."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profil'
    fields = (
        'bio', 'location', 'birth_date', 'website',
        'email_notifications'
    )


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Administration personnalisée pour CustomUser."""
    
    inlines = (UserProfileInline,)
    
    # Champs affichés dans la liste
    list_display = (
        'email', 'first_name', 'last_name', 'user_type',
        'is_active', 'is_staff', 'date_joined'
    )
    
    # Champs pour filtrer
    list_filter = (
        'user_type', 'is_active', 'is_staff', 'is_superuser',
        'date_joined', 'groups'
    )
    
    # Champs de recherche
    search_fields = ('email', 'first_name', 'last_name', 'company')
    
    # Ordre par défaut
    ordering = ('-date_joined',)
    
    # Champs en lecture seule
    readonly_fields = ('date_joined', 'last_login')
    
    # Configuration des fieldsets pour l'édition
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'phone', 'company', 'avatar')
        }),
        ('Permissions', {
            'fields': (
                'user_type', 'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('Dates importantes', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    # Configuration pour l'ajout d'utilisateur
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'user_type',
                'password1', 'password2'
            ),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'groups'),
            'classes': ('collapse',)
        }),
    )
    
    # Actions personnalisées
    actions = ['make_active', 'make_inactive', 'make_admin', 'make_client']
    
    def make_active(self, request, queryset):
        """Active les utilisateurs sélectionnés."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} utilisateur(s) activé(s) avec succès.'
        )
    make_active.short_description = "Activer les utilisateurs sélectionnés"
    
    def make_inactive(self, request, queryset):
        """Désactive les utilisateurs sélectionnés."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} utilisateur(s) désactivé(s) avec succès.'
        )
    make_inactive.short_description = "Désactiver les utilisateurs sélectionnés"
    
    def make_admin(self, request, queryset):
        """Change le type des utilisateurs sélectionnés en admin."""
        updated = queryset.update(user_type='admin')
        # Ajouter au groupe admin
        admin_group, _ = Group.objects.get_or_create(name='admin')
        for user in queryset:
            user.groups.add(admin_group)
        self.message_user(
            request,
            f'{updated} utilisateur(s) changé(s) en administrateur avec succès.'
        )
    make_admin.short_description = "Changer en administrateur"
    
    def make_client(self, request, queryset):
        """Change le type des utilisateurs sélectionnés en client."""
        updated = queryset.update(user_type='client')
        # Ajouter au groupe client
        client_group, _ = Group.objects.get_or_create(name='client')
        for user in queryset:
            user.groups.clear()
            user.groups.add(client_group)
        self.message_user(
            request,
            f'{updated} utilisateur(s) changé(s) en client avec succès.'
        )
    make_client.short_description = "Changer en client"
    
    def get_queryset(self, request):
        """Optimise les requêtes avec select_related et prefetch_related."""
        return super().get_queryset(request).select_related('profile').prefetch_related('groups')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Administration pour UserProfile."""
    
    list_display = (
        'user', 'location', 'email_notifications',
        'created_at'
    )
    
    list_filter = (
        'email_notifications', 'created_at'
    )
    
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'location')
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Informations du profil', {
            'fields': ('bio', 'location', 'birth_date', 'website')
        }),
        ('Préférences', {
            'fields': ('email_notifications',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimise les requêtes avec select_related."""
        return super().get_queryset(request).select_related('user')


# Personnalisation du site d'administration
admin.site.site_header = "Administration SaaS"
admin.site.site_title = "SaaS Admin"
admin.site.index_title = "Bienvenue dans l'administration SaaS"