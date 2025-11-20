"""
Сигналы для отслеживания изменений и создания записей аудита
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import json

from .models import AuditLog, Book, Order, User, Author, Publisher, Stationery


def get_client_ip(request):
    """Получает IP адрес из запроса"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def create_audit_log(instance, action, request=None, changes=None):
    """Создает запись в журнале аудита"""
    user = None
    ip_address = None
    user_agent = None
    
    if request and hasattr(request, 'user'):
        user = request.user if request.user.is_authenticated else None
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # Получаем строковое представление объекта
    object_repr = str(instance)[:255]
    
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=instance.pk,
        object_repr=object_repr,
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )


# Отслеживаемые модели
TRACKED_MODELS = [Book, Order, User, Author, Publisher, Stationery]


@receiver(post_save)
def track_model_changes(sender, instance, created, **kwargs):
    """Отслеживает изменения моделей"""
    if sender not in TRACKED_MODELS:
        return
    
    # Получаем request из thread local (если доступен)
    from django.contrib.auth import get_user
    from django.utils.functional import SimpleLazyObject
    
    try:
        from django.contrib.auth.middleware import get_user as get_user_middleware
        request = getattr(instance, '_request', None)
    except:
        request = None
    
    if created:
        action = 'create'
        changes = {}
    else:
        action = 'update'
        # Получаем изменения из _changed_fields, если они есть
        changes = getattr(instance, '_audit_changes', {})
    
    create_audit_log(instance, action, request, changes)


@receiver(pre_delete)
def track_model_deletion(sender, instance, **kwargs):
    """Отслеживает удаление моделей"""
    if sender not in TRACKED_MODELS:
        return
    
    request = getattr(instance, '_request', None)
    create_audit_log(instance, 'delete', request)


# Middleware для передачи request в модели
class AuditMiddleware:
    """Middleware для передачи request в модели для аудита"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Сохраняем request для использования в сигналах
        response = self.get_response(request)
        return response

