# === IMPORTS ===
from django import forms
# UserCreationForm : Formulaire de base Django pour créer des utilisateurs
# AuthenticationForm : Formulaire de base Django pour l'authentification
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
# authenticate : Fonction Django pour vérifier les identifiants
from django.contrib.auth import authenticate
# Nos modèles personnalisés
from .models import CustomUser, UserProfile


class CustomUserCreationForm(UserCreationForm):
    """
    Formulaire d'inscription personnalisé pour créer de nouveaux utilisateurs.
    
    Étend UserCreationForm de Django pour :
    - Utiliser l'email au lieu du username
    - Ajouter les champs first_name, last_name, user_type
    - Personnaliser les widgets avec des classes CSS Bootstrap
    - Valider l'unicité de l'email
    
    Champs :
        - email : Identifiant unique de l'utilisateur
        - first_name, last_name : Nom complet
        - user_type : Type d'utilisateur (admin/client)
        - password1, password2 : Mot de passe et confirmation
    """
    
    # === CHAMPS DU FORMULAIRE ===
    # Email : remplace le username par défaut de Django
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',  # Classe Bootstrap pour le style
            'placeholder': 'Adresse email'
        })
    )
    
    # Informations personnelles obligatoires
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prénom'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom'
        })
    )
    
    # Type d'utilisateur : détermine les permissions
    user_type = forms.ChoiceField(
        choices=CustomUser.USER_TYPE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    # Mots de passe : redéfinition pour personnaliser les widgets
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le mot de passe'
        })
    )
    
    class Meta:
        model = CustomUser
        # Ordre des champs dans le formulaire
        fields = ('email', 'first_name', 'last_name', 'user_type', 'password1', 'password2')
    
    def clean_email(self):
        """
        Valide l'unicité de l'adresse email.
        
        Returns:
            str: Email validé
            
        Raises:
            ValidationError: Si l'email existe déjà
        """
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Un utilisateur avec cette adresse email existe déjà.')
        return email
    
    def save(self, commit=True):
        """
        Sauvegarde l'utilisateur avec les données du formulaire.
        
        Args:
            commit (bool): Si True, sauvegarde en base de données
            
        Returns:
            CustomUser: Instance de l'utilisateur créé
        """
        # Appel de la méthode parent sans sauvegarder
        user = super().save(commit=False)
        
        # Attribution des champs personnalisés
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.user_type = self.cleaned_data['user_type']
        
        if commit:
            user.save()
            # Note: Le signal post_save créera automatiquement le UserProfile
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """
    Formulaire de connexion personnalisé utilisant l'email comme identifiant.
    
    Étend AuthenticationForm de Django pour :
    - Remplacer le champ username par un champ email
    - Personnaliser les widgets avec des classes CSS Bootstrap
    - Maintenir la logique d'authentification Django
    
    Utilisation :
        - Dans les vues de connexion
        - Validation automatique des identifiants
    """
    
    # === CHAMPS DE CONNEXION ===
    # Redéfinition du champ username en EmailField
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Adresse email',
            'autofocus': True  # Focus automatique sur ce champ
        })
    )
    
    # Champ mot de passe avec style personnalisé
    password = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
    )
    
    def clean(self):
        """
        Valide les identifiants de connexion.
        
        Utilise la fonction authenticate de Django pour vérifier
        que l'email et le mot de passe correspondent à un utilisateur actif.
        
        Returns:
            dict: Données nettoyées du formulaire
            
        Raises:
            ValidationError: Si les identifiants sont incorrects
        """
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username is not None and password:
            # Tentative d'authentification avec email/password
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)
        
        return self.cleaned_data


class UserProfileForm(forms.ModelForm):
    """
    Formulaire pour gérer les informations du profil utilisateur.
    
    Permet de modifier :
    - Les informations personnelles (bio, localisation, date de naissance, site web)
    - Les préférences de notification
    
    Utilisation :
        - Page de profil utilisateur
        - Mise à jour des informations optionnelles
    """
    
    class Meta:
        model = UserProfile
        # Champs modifiables du profil
        fields = [
            'bio', 'location', 'birth_date', 'website',
            'email_notifications', 'newsletter'
        ]
        # Personnalisation des widgets pour chaque champ
        widgets = {
            # Zone de texte pour la biographie
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Parlez-nous de vous...'
            }),
            # Champ texte pour la localisation
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre localisation'
            }),
            # Sélecteur de date HTML5
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            # Champ URL avec validation automatique
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://votre-site.com'
            }),
            # Cases à cocher pour les préférences
            'email_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'newsletter': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class CustomUserUpdateForm(forms.ModelForm):
    """
    Formulaire de mise à jour des informations de base de l'utilisateur.
    
    Permet de modifier :
    - Les informations personnelles (prénom, nom)
    - Les informations de contact (téléphone, entreprise)
    
    Note :
        - L'email ne peut pas être modifié (identifiant unique)
        - Le type d'utilisateur ne peut être changé que par un admin
    """
    
    class Meta:
        model = CustomUser
        # Champs modifiables par l'utilisateur
        fields = ['first_name', 'last_name', 'phone', 'company']
        # Widgets avec styles Bootstrap
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Numéro de téléphone'
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'entreprise'
            }),
        }
    
    def clean_phone(self):
        """
        Valide le format du numéro de téléphone (optionnel).
        
        Returns:
            str: Numéro de téléphone validé
        """
        phone = self.cleaned_data.get('phone')
        if phone:
            # Supprime les espaces et caractères spéciaux
            phone = ''.join(filter(str.isdigit, phone))
            if len(phone) < 10:
                raise forms.ValidationError('Le numéro de téléphone doit contenir au moins 10 chiffres.')
        return phone