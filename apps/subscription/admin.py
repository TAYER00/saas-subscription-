from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Plan, Subscription, SubscriptionHistory


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Administration pour les plans d'abonnement."""
    
    list_display = (
        'name', 'plan_type', 'price_display', 'billing_cycle',
        'max_users', 'is_active', 'is_featured', 'subscription_count'
    )
    
    list_filter = (
        'plan_type', 'billing_cycle', 'is_active', 'is_featured',
        'has_api_access', 'has_priority_support', 'created_at'
    )
    
    search_fields = ('name', 'description')
    
    prepopulated_fields = {'slug': ('name',)}
    
    ordering = ('sort_order', 'price')
    
    readonly_fields = ('created_at', 'updated_at', 'subscription_count')
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'slug', 'description', 'plan_type')
        }),
        ('Tarification', {
            'fields': ('price', 'billing_cycle')
        }),
        ('Limites et quotas', {
            'fields': (
                'max_users', 'max_projects', 'storage_limit_gb'
            ),
            'description': 'Définissez les limites pour ce plan (0 = illimité)'
        }),
        ('Fonctionnalités', {
            'fields': (
                'has_api_access', 'has_priority_support',
                'has_analytics', 'has_custom_branding'
            ),
            'classes': ('collapse',)
        }),
        ('Paramètres d\'affichage', {
            'fields': ('is_active', 'is_featured', 'sort_order')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'subscription_count'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['make_active', 'make_inactive', 'make_featured']
    
    def price_display(self, obj):
        """Affiche le prix formaté."""
        return obj.get_price_display()
    price_display.short_description = 'Prix'
    
    def subscription_count(self, obj):
        """Affiche le nombre d'abonnements actifs pour ce plan."""
        count = obj.subscriptions.filter(status='active').count()
        if count > 0:
            url = reverse('admin:subscription_subscription_changelist')
            return format_html(
                '<a href="{}?plan__id__exact={}">{} abonnement(s)</a>',
                url, obj.id, count
            )
        return '0 abonnement'
    subscription_count.short_description = 'Abonnements actifs'
    
    def make_active(self, request, queryset):
        """Active les plans sélectionnés."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} plan(s) activé(s) avec succès.'
        )
    make_active.short_description = "Activer les plans sélectionnés"
    
    def make_inactive(self, request, queryset):
        """Désactive les plans sélectionnés."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} plan(s) désactivé(s) avec succès.'
        )
    make_inactive.short_description = "Désactiver les plans sélectionnés"
    
    def make_featured(self, request, queryset):
        """Met en avant les plans sélectionnés."""
        updated = queryset.update(is_featured=True)
        self.message_user(
            request,
            f'{updated} plan(s) mis en avant avec succès.'
        )
    make_featured.short_description = "Mettre en avant les plans sélectionnés"


class SubscriptionHistoryInline(admin.TabularInline):
    """Inline pour l'historique des abonnements."""
    model = SubscriptionHistory
    extra = 0
    readonly_fields = ('action', 'old_plan', 'new_plan', 'notes', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Administration pour les abonnements."""
    
    inlines = [SubscriptionHistoryInline]
    
    list_display = (
        'user_email', 'plan_name', 'status', 'amount_paid',
        'start_date', 'end_date', 'days_remaining_display', 'is_trial'
    )
    
    list_filter = (
        'status', 'plan__plan_type', 'is_trial',
        'start_date', 'end_date', 'plan'
    )
    
    search_fields = (
        'user__email', 'user__first_name', 'user__last_name',
        'plan__name', 'transaction_id'
    )
    
    ordering = ('-created_at',)
    
    readonly_fields = (
        'created_at', 'updated_at', 'days_remaining_display'
    )
    
    fieldsets = (
        ('Abonnement', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Dates', {
            'fields': (
                'start_date', 'end_date', 'next_billing_date',
                'trial_end_date', 'days_remaining_display'
            )
        }),
        ('Facturation', {
            'fields': (
                'amount_paid', 'payment_method', 'transaction_id'
            )
        }),
        ('Options', {
            'fields': ('is_trial',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['cancel_subscriptions', 'activate_subscriptions', 'renew_subscriptions']
    
    def user_email(self, obj):
        """Affiche l'email de l'utilisateur avec lien."""
        url = reverse('admin:custom_auth_customuser_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_email.short_description = 'Utilisateur'
    user_email.admin_order_field = 'user__email'
    
    def plan_name(self, obj):
        """Affiche le nom du plan avec lien."""
        url = reverse('admin:subscription_plan_change', args=[obj.plan.id])
        return format_html('<a href="{}">{}</a>', url, obj.plan.name)
    plan_name.short_description = 'Plan'
    plan_name.admin_order_field = 'plan__name'
    
    def days_remaining_display(self, obj):
        """Affiche les jours restants avec couleur."""
        days = obj.days_remaining
        if days is None:
            return 'Illimité'
        
        if days <= 0:
            color = 'red'
            text = 'Expiré'
        elif days <= 7:
            color = 'orange'
            text = f'{days} jour(s)'
        else:
            color = 'green'
            text = f'{days} jour(s)'
        
        return format_html(
            '<span style="color: {};">{}</span>',
            color, text
        )
    days_remaining_display.short_description = 'Jours restants'
    
    def cancel_subscriptions(self, request, queryset):
        """Annule les abonnements sélectionnés."""
        updated = 0
        for subscription in queryset:
            if subscription.status == 'active':
                subscription.cancel()
                updated += 1
        
        self.message_user(
            request,
            f'{updated} abonnement(s) annulé(s) avec succès.'
        )
    cancel_subscriptions.short_description = "Annuler les abonnements sélectionnés"
    
    def activate_subscriptions(self, request, queryset):
        """Active les abonnements sélectionnés."""
        updated = queryset.update(status='active')
        self.message_user(
            request,
            f'{updated} abonnement(s) activé(s) avec succès.'
        )
    activate_subscriptions.short_description = "Activer les abonnements sélectionnés"
    
    def renew_subscriptions(self, request, queryset):
        """Renouvelle les abonnements sélectionnés."""
        updated = 0
        for subscription in queryset:
            if subscription.status in ['cancelled', 'expired']:
                subscription.renew()
                updated += 1
        
        self.message_user(
            request,
            f'{updated} abonnement(s) renouvelé(s) avec succès.'
        )
    renew_subscriptions.short_description = "Renouveler les abonnements sélectionnés"
    
    def get_queryset(self, request):
        """Optimise les requêtes."""
        return super().get_queryset(request).select_related('user', 'plan')


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    """Administration pour l'historique des abonnements."""
    
    list_display = (
        'subscription_user', 'action', 'old_plan_name',
        'new_plan_name', 'created_at'
    )
    
    list_filter = ('action', 'created_at', 'old_plan', 'new_plan')
    
    search_fields = (
        'subscription__user__email',
        'old_plan__name', 'new_plan__name', 'notes'
    )
    
    ordering = ('-created_at',)
    
    readonly_fields = (
        'subscription', 'action', 'old_plan', 'new_plan',
        'notes', 'created_at'
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def subscription_user(self, obj):
        """Affiche l'utilisateur de l'abonnement."""
        return obj.subscription.user.email
    subscription_user.short_description = 'Utilisateur'
    subscription_user.admin_order_field = 'subscription__user__email'
    
    def old_plan_name(self, obj):
        """Affiche le nom de l'ancien plan."""
        return obj.old_plan.name if obj.old_plan else '-'
    old_plan_name.short_description = 'Ancien plan'
    
    def new_plan_name(self, obj):
        """Affiche le nom du nouveau plan."""
        return obj.new_plan.name if obj.new_plan else '-'
    new_plan_name.short_description = 'Nouveau plan'
    
    def get_queryset(self, request):
        """Optimise les requêtes."""
        return super().get_queryset(request).select_related(
            'subscription__user', 'old_plan', 'new_plan'
        )