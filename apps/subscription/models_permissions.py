# -*- coding: utf-8 -*-
"""
Modèle de gestion des permissions temporaires pour les abonnements.

Ce module gère :
- Les permissions associées aux plans payants
- La durée de validité des permissions
- L'expiration automatique des permissions
- Le renouvellement des permissions
"""

from django.db import models
from django.contrib.auth.models import Permission
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from .models import Subscription, Plan
from apps.auth.models import CustomUser


class PlanPermission(models.Model):
    """
    Modèle pour associer des permissions spécifiques à un plan d'abonnement.
    
    Chaque plan peut avoir plusieurs permissions qui définissent
    les fonctionnalités accessibles aux utilisateurs de ce plan.
    """
    plan = models.ForeignKey(
        Plan, 
        on_delete=models.CASCADE, 
        related_name='plan_permissions',
        verbose_name="Plan d'abonnement"
    )
    permission = models.ForeignKey(
        Permission, 
        on_delete=models.CASCADE,
        verbose_name="Permission"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Permission active",
        help_text="Indique si cette permission est active pour ce plan"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    
    class Meta:
        unique_together = ('plan', 'permission')
        verbose_name = "Permission de plan"
        verbose_name_plural = "Permissions de plans"
        ordering = ['plan__name', 'permission__name']
    
    def __str__(self):
        return f"{self.plan.name} - {self.permission.name}"


class UserTemporaryPermission(models.Model):
    """
    Modèle pour gérer les permissions temporaires accordées aux utilisateurs.
    
    Ces permissions sont accordées lors de l'activation d'un plan payant
    et expirent automatiquement après une durée définie.
    """
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='temporary_permissions',
        verbose_name="Utilisateur"
    )
    permission = models.ForeignKey(
        Permission, 
        on_delete=models.CASCADE,
        verbose_name="Permission"
    )
    subscription = models.ForeignKey(
        Subscription, 
        on_delete=models.CASCADE, 
        related_name='temporary_permissions',
        verbose_name="Abonnement",
        help_text="L'abonnement qui a accordé cette permission"
    )
    granted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date d'attribution"
    )
    expires_at = models.DateTimeField(
        verbose_name="Date d'expiration",
        help_text="Date à laquelle cette permission expire"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Permission active",
        help_text="Indique si cette permission est actuellement active"
    )
    revoked_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Date de révocation",
        help_text="Date à laquelle cette permission a été révoquée manuellement"
    )
    
    # Champ de test pour le changement de couleur de fond
    test_background_color = models.CharField(
        max_length=20,
        default='yellow',
        verbose_name="Couleur de fond de test",
        help_text="Couleur de fond pour tester les permissions d'abonnement payant (jaune par défaut)"
    )
    
    class Meta:
        unique_together = ('user', 'permission', 'subscription')
        verbose_name = "Permission temporaire utilisateur"
        verbose_name_plural = "Permissions temporaires utilisateurs"
        ordering = ['-granted_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['expires_at', 'is_active']),
        ]
    
    def __str__(self):
        status = "Active" if self.is_active and not self.is_expired else "Inactive"
        return f"{self.user.email} - {self.permission.name} ({status})"
    
    @property
    def is_expired(self):
        """
        Vérifie si la permission a expiré.
        
        Returns:
            bool: True si la permission a expiré, False sinon
        """
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """
        Vérifie si la permission est valide (active et non expirée).
        
        Returns:
            bool: True si la permission est valide, False sinon
        """
        return self.is_active and not self.is_expired and not self.revoked_at
    
    def revoke(self):
        """
        Révoque manuellement cette permission.
        
        Cette méthode marque la permission comme révoquée
        et la désactive immédiatement.
        """
        self.is_active = False
        self.revoked_at = timezone.now()
        self.save(update_fields=['is_active', 'revoked_at'])
    
    def extend_expiration(self, days=None, hours=None):
        """
        Prolonge la durée de validité de cette permission.
        
        Args:
            days (int, optional): Nombre de jours à ajouter
            hours (int, optional): Nombre d'heures à ajouter
        """
        if days:
            self.expires_at += timedelta(days=days)
        if hours:
            self.expires_at += timedelta(hours=hours)
        self.save(update_fields=['expires_at'])
    
    def save(self, *args, **kwargs):
        """
        Sauvegarde personnalisée pour gérer l'expiration automatique.
        
        Si la permission a expiré, elle est automatiquement désactivée.
        """
        if self.is_expired and self.is_active:
            self.is_active = False
        super().save(*args, **kwargs)


class PermissionMigrationLog(models.Model):
    """
    Journal des migrations de permissions pour traçabilité.
    
    Ce modèle enregistre toutes les opérations de migration
    de permissions pour audit et débogage.
    """
    ACTION_CHOICES = [
        ('GRANT', 'Permission accordée'),
        ('REVOKE', 'Permission révoquée'),
        ('EXPIRE', 'Permission expirée'),
        ('RENEW', 'Permission renouvelée'),
        ('MIGRATE', 'Migration de plan'),
    ]
    
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='permission_logs',
        verbose_name="Utilisateur"
    )
    action = models.CharField(
        max_length=10, 
        choices=ACTION_CHOICES,
        verbose_name="Action"
    )
    permission = models.ForeignKey(
        Permission, 
        on_delete=models.CASCADE,
        verbose_name="Permission"
    )
    old_plan = models.ForeignKey(
        Plan, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='migration_logs_old',
        verbose_name="Ancien plan"
    )
    new_plan = models.ForeignKey(
        Plan, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='migration_logs_new',
        verbose_name="Nouveau plan"
    )
    subscription = models.ForeignKey(
        Subscription, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name="Abonnement"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Horodatage"
    )
    details = models.TextField(
        blank=True,
        verbose_name="Détails",
        help_text="Informations supplémentaires sur l'action"
    )
    
    class Meta:
        verbose_name = "Journal de migration de permission"
        verbose_name_plural = "Journaux de migration de permissions"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_action_display()} - {self.permission.name}"