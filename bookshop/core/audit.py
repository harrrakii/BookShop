"""
Утилиты для аудита всех действий пользователей
"""
from .models import AuditLog


def get_client_ip(request):
    """Получает IP адрес из запроса"""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def get_user_agent(request):
    """Получает User Agent из запроса"""
    if not request:
        return None
    return request.META.get('HTTP_USER_AGENT', '')


def log_action(action, user=None, request=None, model_name=None, object_id=None, 
               object_repr=None, description=None, changes=None, url_path=None):
    """
    Создает запись в журнале аудита для любого действия
    
    Args:
        action: Тип действия ('login', 'logout', 'view', 'create', 'update', 'delete', 'download', 'export', 'import', 'config', 'other')
        user: Пользователь (если None, берется из request)
        request: HTTP request (для получения IP, user agent, URL)
        model_name: Название модели (если применимо)
        object_id: ID объекта (если применимо)
        object_repr: Строковое представление объекта
        description: Описание действия
        changes: Словарь изменений {field: {'old': value, 'new': value}} (для create/update)
        url_path: URL страницы (если не указан, берется из request)
    """
    # Получаем пользователя из request, если не передан
    if user is None and request and hasattr(request, 'user'):
        user = request.user if request.user.is_authenticated else None
    
    # Получаем IP адрес и User Agent
    ip_address = get_client_ip(request) if request else None
    user_agent = get_user_agent(request) if request else None
    
    # Получаем URL из request, если не указан
    if url_path is None and request:
        url_path = request.path[:500]  # Ограничиваем длину
    
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        object_repr=object_repr[:255] if object_repr else None,
        description=description,
        url_path=url_path,
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )


def log_change(instance, action, user=None, request=None, changes=None):
    """
    Создает запись в журнале аудита для изменений моделей (обратная совместимость)
    
    Args:
        instance: Экземпляр модели
        action: 'create', 'update' или 'delete'
        user: Пользователь, внесший изменение
        request: HTTP request (для получения IP и user agent)
        changes: Словарь изменений {field: {'old': value, 'new': value}}
    """
    # Получаем строковое представление объекта
    try:
        object_repr = str(instance)[:255]
    except:
        object_repr = f"{instance.__class__.__name__} #{instance.pk}"
    
    log_action(
        action=action,
        user=user,
        request=request,
        model_name=instance.__class__.__name__,
        object_id=instance.pk,
        object_repr=object_repr,
        changes=changes or {},
    )
