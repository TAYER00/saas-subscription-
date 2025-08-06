from django.contrib import admin
from .models import TenderSite, Tender, TenderDocument, ScrapingLog


@admin.register(TenderSite)
class TenderSiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'is_active', 'last_scraped', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'url']
    readonly_fields = ['created_at', 'updated_at']


class TenderDocumentInline(admin.TabularInline):
    model = TenderDocument
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ['title', 'organization', 'site', 'status', 'deadline_date', 'scraped_at']
    list_filter = ['status', 'category', 'site', 'scraped_at']
    search_fields = ['title', 'organization', 'reference']
    readonly_fields = ['content_hash', 'scraped_at', 'updated_at']
    date_hierarchy = 'deadline_date'
    inlines = [TenderDocumentInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('title', 'reference', 'description', 'category', 'status')
        }),
        ('Organisme', {
            'fields': ('organization', 'contact_person', 'contact_email', 'contact_phone')
        }),
        ('Dates', {
            'fields': ('publication_date', 'deadline_date', 'opening_date')
        }),
        ('Informations financières', {
            'fields': ('estimated_value', 'currency')
        }),
        ('Localisation', {
            'fields': ('location', 'region')
        }),
        ('Métadonnées', {
            'fields': ('site', 'source_url', 'content_hash', 'scraped_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(TenderDocument)
class TenderDocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'tender', 'document_type', 'downloaded', 'created_at']
    list_filter = ['document_type', 'downloaded', 'created_at']
    search_fields = ['name', 'tender__title']
    readonly_fields = ['created_at']


@admin.register(ScrapingLog)
class ScrapingLogAdmin(admin.ModelAdmin):
    list_display = ['site', 'status', 'items_found', 'items_new', 'items_updated', 'started_at', 'duration_display']
    list_filter = ['status', 'site', 'started_at']
    search_fields = ['site__name', 'error_message']
    readonly_fields = ['started_at', 'duration_display']
    date_hierarchy = 'started_at'
    
    def duration_display(self, obj):
        return obj.duration or '-'
    duration_display.short_description = 'Durée'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('site', 'status')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'execution_time')
        }),
        ('Statistiques', {
            'fields': ('items_found', 'items_new', 'items_updated')
        }),
        ('Erreurs', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        })
    )
