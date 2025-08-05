#!/usr/bin/env python
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

def create_test_users():
    # Créer le compte admin
    admin_email = "admin@test.com"
    admin_password = "123456"
    
    # Vérifier si l'utilisateur admin existe déjà
    if User.objects.filter(email=admin_email).exists():
        print(f"L'utilisateur {admin_email} existe déjà.")
        admin_user = User.objects.get(email=admin_email)
    else:
        admin_user = User.objects.create_user(
            email=admin_email,
            password=admin_password,
            first_name="Admin",
            last_name="Test",
            is_staff=True,
            is_superuser=True
        )
        print(f"Utilisateur admin créé: {admin_email}")
    
    # Ajouter au groupe admin
    admin_group = Group.objects.get(name='admin')
    admin_user.groups.add(admin_group)
    
    # Créer le compte utilisateur normal
    user_email = "user@test.com"
    user_password = "123456"
    
    # Vérifier si l'utilisateur existe déjà
    if User.objects.filter(email=user_email).exists():
        print(f"L'utilisateur {user_email} existe déjà.")
        regular_user = User.objects.get(email=user_email)
    else:
        regular_user = User.objects.create_user(
            email=user_email,
            password=user_password,
            first_name="User",
            last_name="Test"
        )
        print(f"Utilisateur normal créé: {user_email}")
    
    # Ajouter au groupe client
    client_group = Group.objects.get(name='client')
    regular_user.groups.add(client_group)
    
    print("\n=== COMPTES DE TEST CRÉÉS ===")
    print(f"Admin: {admin_email} / {admin_password}")
    print(f"User: {user_email} / {user_password}")
    print("\nVous pouvez maintenant vous connecter avec ces comptes.")

if __name__ == "__main__":
    create_test_users()