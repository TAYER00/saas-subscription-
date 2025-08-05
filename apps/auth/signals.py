from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import CustomUser, UserProfile


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Crée automatiquement un profil utilisateur lors de la création d'un utilisateur."""
    if created:
        UserProfile.objects.create(user=instance)
        
        # Assigner automatiquement l'utilisateur au groupe approprié
        if instance.user_type == 'admin':
            admin_group, _ = Group.objects.get_or_create(name='admin')
            instance.groups.add(admin_group)
        elif instance.user_type == 'client':
            client_group, _ = Group.objects.get_or_create(name='client')
            instance.groups.add(client_group)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    """Sauvegarde le profil utilisateur lors de la sauvegarde de l'utilisateur."""
    if hasattr(instance, 'profile'):
        instance.profile.save()