# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('custom_auth', '0002_alter_userprofile_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PasswordResetToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(help_text='Token unique pour la réinitialisation', max_length=100, unique=True, verbose_name='Token')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Créé le')),
                ('expires_at', models.DateTimeField(help_text="Date et heure d'expiration du token", verbose_name='Expire le')),
                ('used', models.BooleanField(default=False, help_text='Indique si le token a déjà été utilisé', verbose_name='Utilisé')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_reset_tokens', to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur')),
            ],
            options={
                'verbose_name': 'Token de réinitialisation',
                'verbose_name_plural': 'Tokens de réinitialisation',
                'db_table': 'auth_password_reset_token',
                'ordering': ['-created_at'],
            },
        ),
    ]