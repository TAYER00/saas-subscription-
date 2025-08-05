# 🚀 SaaS Subscription Platform - Documentation Complète

## 📌 Présentation du projet

Cette plateforme SaaS (Software as a Service) est développée avec Django et permet la gestion d'abonnements avec différents types d'utilisateurs. Le système comprend :

- **Authentification personnalisée** avec deux types d'utilisateurs (Admin/Client)
- **Système d'abonnements** avec différents plans tarifaires
- **Interface d'administration** pour gérer les utilisateurs et abonnements
- **Dashboard personnalisé** selon le type d'utilisateur
- **API REST** pour l'intégration avec d'autres services

### Technologies utilisées
- **Backend** : Django 4.x, Python 3.x
- **Base de données** : SQLite (développement), PostgreSQL (production)
- **Frontend** : HTML5, Tailwind CSS, JavaScript
- **API** : Django REST Framework
- **Authentification** : Django Auth avec modèle utilisateur personnalisé

---

## 🧱 Arborescence des fichiers

```
Saas subscription/
├── apps/                          # Applications Django
│   ├── auth/                      # Gestion de l'authentification
│   ├── dashboard/                 # Tableau de bord
│   └── subscription/              # Gestion des abonnements
├── config/                        # Configuration du projet
│   ├── settings/                  # Paramètres par environnement
│   ├── urls.py                    # URLs principales
│   └── wsgi.py                    # Configuration WSGI
├── templates/                     # Templates HTML
│   ├── auth/                      # Templates d'authentification
│   ├── subscription/              # Templates d'abonnements
│   └── base.html                  # Template de base
├── static/                        # Fichiers statiques (CSS, JS, images)
├── media/                         # Fichiers uploadés par les utilisateurs
├── requirements.txt               # Dépendances Python
├── manage.py                      # Script de gestion Django
└── db.sqlite3                     # Base de données SQLite
```

### 📁 Explication des dossiers principaux

#### `apps/` - Applications Django
- **`auth/`** : Gestion complète de l'authentification, permissions, et profils utilisateurs
- **`dashboard/`** : Interface principale après connexion, adaptée selon le type d'utilisateur
- **`subscription/`** : Gestion des plans d'abonnement, souscriptions, et historique

#### `config/` - Configuration du projet
- **`settings/`** : Paramètres séparés par environnement (base, dev, prod)
- **`urls.py`** : Routage principal de l'application
- **`wsgi.py`** : Configuration pour le déploiement

#### `templates/` - Interface utilisateur
- **`base.html`** : Template principal avec navigation conditionnelle
- **`auth/`** : Pages de connexion, inscription, profil
- **`subscription/`** : Pages de gestion des abonnements

---

## 🔐 Système d'authentification

### Modèle utilisateur personnalisé (`apps/auth/models.py`)

La classe `CustomUser` étend `AbstractBaseUser` et `PermissionsMixin` :

```python
class CustomUser(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = [
        ('admin', 'Administrateur'),
        ('client', 'Client'),
    ]
    
    email = models.EmailField(unique=True)  # Email comme identifiant
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    # ... autres champs
```

**Caractéristiques principales :**
- **Email comme identifiant** : Remplace le username par défaut
- **Deux types d'utilisateurs** : `admin` et `client`
- **Profil étendu** : Modèle `UserProfile` lié en OneToOne
- **Méthodes utilitaires** : `is_admin()`, `is_client()`, `get_full_name()`

### Création des groupes et permissions (`apps/auth/management/commands/init_roles.py`)

Le système utilise les groupes Django pour gérer les permissions :

```python
# Création automatique des groupes
admin_group, created = Group.objects.get_or_create(name='admin')
client_group, created = Group.objects.get_or_create(name='client')

# Attribution des permissions
admin_group.permissions.set(Permission.objects.all())  # Toutes les permissions
client_group.permissions.set([...])  # Permissions limitées
```

**Commande d'initialisation :**
```bash
python manage.py init_roles
```

### Gestion des droits dans le backend

#### Décorateurs personnalisés (`apps/auth/permissions.py`)

```python
@admin_required
def admin_only_view(request):
    # Vue accessible uniquement aux administrateurs
    pass

@client_required  
def client_only_view(request):
    # Vue accessible uniquement aux clients
    pass

@permission_required_custom('auth.view_customuser')
def permission_based_view(request):
    # Vue basée sur une permission spécifique
    pass
```

#### Mixins pour les vues basées sur les classes

```python
class AdminOnlyView(AdminRequiredMixin, ListView):
    # Vue accessible uniquement aux admins
    pass

class ClientOnlyView(ClientRequiredMixin, DetailView):
    # Vue accessible uniquement aux clients
    pass
```

#### Vérification des permissions

```python
# Dans les vues
if request.user.has_perm('subscription.add_subscription'):
    # L'utilisateur peut créer des abonnements
    pass

# Dans les templates
{% if user.is_admin %}
    <!-- Contenu admin uniquement -->
{% endif %}
```

---

## 🖥️ Interface et affichage conditionnel

### Navigation adaptative (`templates/base.html`)

La navigation s'adapte automatiquement selon le type d'utilisateur :

```html
{% if user.is_authenticated %}
    {% if user.is_admin %}
        <!-- Menu administration -->
        <div class="relative dropdown">
            <button>Administration</button>
            <div class="dropdown-menu">
                <a href="{% url 'auth:user_list' %}">Utilisateurs</a>
                <a href="{% url 'subscription:admin_subscriptions' %}">Abonnements</a>
                <a href="{% url 'subscription:admin_plans' %}">Plans</a>
            </div>
        </div>
    {% else %}
        <!-- Menu client -->
        <a href="{% url 'subscription:plans' %}">Plans</a>
        <a href="{% url 'subscription:my_subscription' %}">Mon Abonnement</a>
    {% endif %}
{% else %}
    <!-- Menu utilisateur non connecté -->
    <a href="{% url 'auth:login' %}">Connexion</a>
    <a href="{% url 'auth:register' %}">Inscription</a>
{% endif %}
```

### Exemples de boutons conditionnels

```html
<!-- Bouton d'abonnement conditionnel -->
{% if user.is_authenticated %}
    {% if current_subscription %}
        {% if current_subscription.plan == plan %}
            <button class="btn btn-secondary" disabled>
                <i class="fas fa-check"></i> Plan actuel
            </button>
        {% else %}
            <a href="{% url 'subscription:change_plan' plan.id %}" class="btn btn-warning">
                <i class="fas fa-exchange-alt"></i> Changer de plan
            </a>
        {% endif %}
    {% else %}
        <a href="{% url 'subscription:subscribe' plan.id %}" class="btn btn-primary">
            <i class="fas fa-credit-card"></i> S'abonner
        </a>
    {% endif %}
{% else %}
    <a href="{% url 'auth:login' %}" class="btn btn-primary">
        <i class="fas fa-sign-in-alt"></i> Se connecter pour s'abonner
    </a>
{% endif %}
```

### Affichage des informations utilisateur

```html
<!-- Badge de type d'utilisateur -->
<div class="text-xs text-gray-500">
    {% if user.is_admin %}
        <span class="bg-red-100 text-red-800 px-2 py-1 rounded">Administrateur</span>
    {% else %}
        <span class="bg-blue-100 text-blue-800 px-2 py-1 rounded">Client</span>
    {% endif %}
</div>
```

---

## 🔄 Workflow complet d'un utilisateur

### 1. Inscription et connexion

1. **Inscription** (`/auth/register/`)
   - Formulaire : `CustomUserCreationForm` dans `apps/auth/forms.py`
   - Vue : `RegisterView` dans `apps/auth/views.py`
   - Validation de l'email unique
   - Création automatique du profil utilisateur (signal)
   - Attribution automatique au groupe 'client'

2. **Connexion** (`/auth/login/`)
   - Formulaire : `CustomAuthenticationForm` avec email
   - Vue : `CustomLoginView`
   - Redirection vers le dashboard

### 2. Accès au dashboard

1. **Redirection automatique** après connexion vers `/dashboard/`
2. **Affichage conditionnel** selon le type d'utilisateur :
   - **Admin** : Statistiques globales, gestion des utilisateurs
   - **Client** : Informations personnelles, statut d'abonnement

### 3. Gestion des abonnements

#### Pour les clients :

1. **Consultation des plans** (`/subscription/plans/`)
   - Vue : `PlanListView` dans `apps/subscription/views.py`
   - Affichage de tous les plans actifs
   - Comparaison avec l'abonnement actuel

2. **Souscription** (`/subscription/subscribe/<plan_id>/`)
   - Vue : `subscribe_to_plan`
   - Création d'un objet `Subscription`
   - Enregistrement dans l'historique

3. **Gestion de l'abonnement** (`/subscription/my-subscription/`)
   - Vue : `my_subscription`
   - Affichage des détails de l'abonnement
   - Options de modification/annulation

#### Pour les administrateurs :

1. **Gestion des utilisateurs** (`/auth/users/`)
   - Vue : `UserListView` avec `AdminRequiredMixin`
   - Activation/désactivation des comptes
   - Changement de type d'utilisateur

2. **Gestion des abonnements** (`/subscription/admin/subscriptions/`)
   - Vue : `AdminSubscriptionListView`
   - Vue d'ensemble de tous les abonnements
   - Statistiques et filtres

---

## ⚙️ Modifications et extensions

### Ajouter un nouveau rôle

1. **Modifier le modèle** (`apps/auth/models.py`) :
```python
USER_TYPE_CHOICES = [
    ('admin', 'Administrateur'),
    ('client', 'Client'),
    ('manager', 'Manager'),  # Nouveau rôle
]
```

2. **Créer les permissions** (`apps/auth/management/commands/init_roles.py`) :
```python
manager_group, created = Group.objects.get_or_create(name='manager')
manager_permissions = [
    'view_customuser',
    'view_subscription',
    # Permissions spécifiques au manager
]
manager_group.permissions.set(manager_permissions)
```

3. **Ajouter les décorateurs** (`apps/auth/permissions.py`) :
```python
@manager_required
def manager_only_view(request):
    if not request.user.user_type == 'manager':
        # Gestion de l'erreur
    pass
```

4. **Mettre à jour les templates** (`templates/base.html`) :
```html
{% elif user.user_type == 'manager' %}
    <!-- Menu spécifique au manager -->
{% endif %}
```

### Ajouter un type de plan

1. **Modifier le modèle** (`apps/subscription/models.py`) :
```python
PLAN_TYPE_CHOICES = [
    ('free', 'Gratuit'),
    ('basic', 'Basique'),
    ('premium', 'Premium'),
    ('enterprise', 'Entreprise'),
    ('custom', 'Personnalisé'),  # Nouveau type
]
```

2. **Ajouter les fonctionnalités** :
```python
has_custom_feature = models.BooleanField('Fonctionnalité personnalisée', default=False)
custom_limit = models.PositiveIntegerField('Limite personnalisée', default=0)
```

3. **Mettre à jour les templates** (`templates/subscription/plans.html`) :
```html
{% if plan.plan_type == 'custom' %}
    <span class="badge badge-custom">Personnalisé</span>
{% endif %}
```

### Ajouter des règles d'accès

1. **Créer de nouvelles permissions** (`apps/auth/permissions.py`) :
```python
def subscription_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.subscriptions.filter(status='active').exists():
            messages.error(request, 'Abonnement actif requis.')
            return redirect('subscription:plans')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
```

2. **Appliquer aux vues** :
```python
@subscription_required
def premium_feature_view(request):
    # Vue accessible uniquement aux abonnés
    pass
```

---

## 🛠️ Astuces de développement

### Commandes utiles

```bash
# Initialiser les rôles et permissions
python manage.py init_roles

# Créer un superutilisateur
python manage.py createsuperuser

# Appliquer les migrations
python manage.py makemigrations
python manage.py migrate

# Collecter les fichiers statiques
python manage.py collectstatic

# Lancer le serveur de développement
python manage.py runserver
```

### Vérification des droits

```python
# Dans les vues
if request.user.has_perm('subscription.view_subscription'):
    # L'utilisateur peut voir les abonnements
    pass

# Vérifier le groupe
if request.user.groups.filter(name='admin').exists():
    # L'utilisateur est dans le groupe admin
    pass

# Vérifier le type d'utilisateur
if request.user.is_admin:
    # Méthode personnalisée du modèle
    pass
```

### Debugging et logs

```python
# Dans settings/dev.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

### Tests et validation

```python
# Tester les permissions
from django.test import TestCase
from django.contrib.auth.models import Group
from apps.auth.models import CustomUser

class PermissionTestCase(TestCase):
    def setUp(self):
        self.admin_user = CustomUser.objects.create_user(
            email='admin@test.com',
            password='test123',
            user_type='admin'
        )
        
    def test_admin_permissions(self):
        self.assertTrue(self.admin_user.is_admin)
        self.assertTrue(self.admin_user.has_perm('auth.view_customuser'))
```

### Sécurité

- **Toujours valider les permissions** dans les vues
- **Utiliser HTTPS** en production
- **Configurer CORS** correctement
- **Valider les données** côté serveur
- **Utiliser les décorateurs** `@login_required` et `@admin_required`

### Performance

- **Utiliser `select_related()`** pour les relations ForeignKey
- **Utiliser `prefetch_related()`** pour les relations ManyToMany
- **Indexer les champs** fréquemment recherchés
- **Mettre en cache** les requêtes coûteuses

---

## 📚 Ressources supplémentaires

- [Documentation Django](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Font Awesome](https://fontawesome.com/)

---

**Développé avec ❤️ en Django**