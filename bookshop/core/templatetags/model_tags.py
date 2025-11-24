from django import template
import builtins

register = template.Library()


@register.filter
def getattr(obj, attr):
    """Получает атрибут объекта"""
    try:
        value = builtins.getattr(obj, str(attr), None)
        if value is not None:
            # Обрабатываем разные типы
            if hasattr(value, '__str__'):
                return str(value)
            return value
        return None
    except (AttributeError, TypeError):
        return None

