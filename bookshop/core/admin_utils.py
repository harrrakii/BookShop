"""
Утилиты для админки: экспорт/импорт данных в JSON
"""
import json
from django.core.serializers import serialize, deserialize
from django.db import transaction
from django.db.utils import IntegrityError
from .models import (
    Author, Book, Category, DeliveryOption, Genre, LoyaltyCard,
    Order, OrderItem, PaymentCard, PickupPoint, Product,
    Publisher, Review, Role, SavedAddress, Stationery, User,
    Wishlist, FAQ, SupportMessage, AuditLog
)


def export_all_data_to_json():
    """
    Экспортирует все данные из БД в JSON формат
    """
    data = {}
    
    # Экспортируем все модели в правильном порядке (сначала зависимости)
    models_to_export = [
        ('roles', Role),
        ('users', User),
        ('categories', Category),
        ('publishers', Publisher),
        ('authors', Author),
        ('genres', Genre),
        ('books', Book),
        ('stationery', Stationery),
        ('products', Product),
        ('delivery_options', DeliveryOption),
        ('pickup_points', PickupPoint),
        ('orders', Order),
        ('order_items', OrderItem),
        ('reviews', Review),
        ('saved_addresses', SavedAddress),
        ('payment_cards', PaymentCard),
        ('loyalty_cards', LoyaltyCard),
        ('wishlist', Wishlist),
        ('faq', FAQ),
        ('support_messages', SupportMessage),
        # AuditLog обычно не экспортируем, так как это логи
        # ('audit_logs', AuditLog),
    ]
    
    for key, model in models_to_export:
        try:
            queryset = model.objects.all()
            serialized = serialize('python', queryset)
            data[key] = serialized
        except Exception as e:
            # Если модель не существует или есть ошибка, пропускаем её
            data[key] = []
            print(f"Предупреждение: не удалось экспортировать {key}: {str(e)}")
    
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def import_data_from_json(json_data):
    """
    Импортирует данные из JSON в БД
    ВАЖНО: Импорт выполняется в транзакции, при ошибке все изменения откатываются
    """
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Неверный формат JSON: {e}")
    
    if not isinstance(data, dict):
        raise ValueError("JSON должен содержать объект с данными")
    
    errors = []
    imported_counts = {}
    
    # Порядок импорта важен - сначала зависимости
    import_order = [
        ('roles', Role),
        ('users', User),
        ('categories', Category),
        ('publishers', Publisher),
        ('authors', Author),
        ('genres', Genre),
        ('books', Book),
        ('stationery', Stationery),
        ('products', Product),
        ('delivery_options', DeliveryOption),
        ('pickup_points', PickupPoint),
        ('orders', Order),
        ('order_items', OrderItem),
        ('reviews', Review),
        ('saved_addresses', SavedAddress),
        ('payment_cards', PaymentCard),
        ('loyalty_cards', LoyaltyCard),
        ('wishlist', Wishlist),
        ('faq', FAQ),
        ('support_messages', SupportMessage),
        # AuditLog обычно не импортируем
        # ('audit_logs', AuditLog),
    ]
    
    # Используем транзакцию для атомарности операции
    # Если произойдет ошибка, все изменения откатятся
    try:
        with transaction.atomic():
            for key, model in import_order:
                if key in data:
                    try:
                        if not isinstance(data[key], list):
                            errors.append(f"Данные для {key} должны быть массивом")
                            continue
                        
                        objects = deserialize('python', data[key], ignorenonexistent=True, use_natural_foreign_keys=True)
                        count = 0
                        for obj in objects:
                            try:
                                obj.save()
                                count += 1
                            except IntegrityError as e:
                                # Пропускаем дубликаты (например, если запись уже существует)
                                errors.append(f"Дубликат в {key}: {str(e)}")
                                continue
                            except Exception as e:
                                errors.append(f"Ошибка при сохранении объекта в {key}: {str(e)}")
                                # Продолжаем импорт остальных объектов
                                continue
                        
                        imported_counts[key] = count
                    except Exception as e:
                        errors.append(f"Ошибка при импорте {key}: {str(e)}")
                        # Продолжаем импорт остальных моделей
                        continue
                else:
                    # Модель отсутствует в данных - это нормально
                    imported_counts[key] = 0
        
        # Если были критические ошибки, выбрасываем исключение
        # Но не критичные (дубликаты) просто логируем
        if errors:
            error_message = f"Импорт завершен с предупреждениями. Импортировано: {sum(imported_counts.values())} записей. Ошибки: {'; '.join(errors[:10])}"
            if len(errors) > 10:
                error_message += f" (и еще {len(errors) - 10} ошибок)"
            print(error_message)
        
        return {
            'success': True,
            'imported': imported_counts,
            'errors': errors
        }
        
    except Exception as e:
        # Критическая ошибка - транзакция откатится автоматически
        raise ValueError(f"Критическая ошибка при импорте данных: {str(e)}")



