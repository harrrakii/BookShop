# Generated manually

from django.db import migrations


def create_default_roles(apps, schema_editor):
    """Создает роли по умолчанию: пользователь, менеджер, админ"""
    Role = apps.get_model('core', 'Role')
    
    # Создаем роли, если их еще нет
    Role.objects.get_or_create(name='пользователь')
    Role.objects.get_or_create(name='менеджер')
    Role.objects.get_or_create(name='админ')


def reverse_create_default_roles(apps, schema_editor):
    """Удаляет роли по умолчанию при откате миграции"""
    Role = apps.get_model('core', 'Role')
    Role.objects.filter(name__in=['пользователь', 'менеджер', 'админ']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_user_birth_date_loyaltycard'),
    ]

    operations = [
        migrations.RunPython(create_default_roles, reverse_create_default_roles),
    ]



