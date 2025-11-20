"""
Утилиты для админки: экспорт/импорт данных в JSON
"""
import json
from django.core.serializers import serialize, deserialize
from django.db import transaction
from .models import (
    Author, Book, Category, DeliveryOption, Genre, LoyaltyCard,
    Order, OrderItem, PaymentCard, PickupPoint, Product,
    Publisher, Review, Role, SavedAddress, Stationery, User
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
    ]
    
    for key, model in models_to_export:
        queryset = model.objects.all()
        serialized = serialize('python', queryset)
        data[key] = serialized
    
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def import_data_from_json(json_data):
    """
    Импортирует данные из JSON в БД
    """
    try:
        data = json.loads(json_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Неверный формат JSON: {e}")
    
    errors = []
    
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
    ]
    
    with transaction.atomic():
        for key, model in import_order:
            if key in data:
                try:
                    objects = deserialize('python', data[key], ignorenonexistent=True, use_natural_foreign_keys=True)
                    for obj in objects:
                        obj.save()
                except Exception as e:
                    errors.append(f"Ошибка при импорте {key}: {str(e)}")
                    # Не прерываем выполнение, продолжаем импорт остальных моделей
                    pass
    
    if errors:
        raise ValueError("Ошибки при импорте: " + "; ".join(errors))
    
    return True

