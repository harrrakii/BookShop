"""
Views для админ-панели на сайте (не Django admin)
Позволяет админу редактировать все модели прямо на сайте
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import models
from django.apps import apps
from django.forms import modelform_factory
from django.http import JsonResponse

from .views_manager import admin_required
from .models import (
    Book, Author, Publisher, Stationery, Category, Genre,
    Order, User, Review, DeliveryOption, PickupPoint,
    SavedAddress, PaymentCard, LoyaltyCard, FAQ, SupportMessage, Role
)
from .audit import log_action


# Маппинг моделей для удобного доступа
MODEL_MAP = {
    'book': Book,
    'author': Author,
    'publisher': Publisher,
    'stationery': Stationery,
    'category': Category,
    'genre': Genre,
    'order': Order,
    'user': User,
    'review': Review,
    'deliveryoption': DeliveryOption,
    'pickuppoint': PickupPoint,
    'savedaddress': SavedAddress,
    'paymentcard': PaymentCard,
    'loyaltycard': LoyaltyCard,
    'faq': FAQ,
    'supportmessage': SupportMessage,
    'role': Role,
}

MODEL_NAMES = {
    'book': 'Книги',
    'author': 'Авторы',
    'publisher': 'Издатели',
    'stationery': 'Канцтовары',
    'category': 'Категории',
    'genre': 'Жанры',
    'order': 'Заказы',
    'user': 'Пользователи',
    'review': 'Отзывы',
    'deliveryoption': 'Варианты доставки',
    'pickuppoint': 'Пункты выдачи',
    'savedaddress': 'Сохраненные адреса',
    'paymentcard': 'Платежные карты',
    'loyaltycard': 'Карты лояльности',
    'faq': 'FAQ',
    'supportmessage': 'Сообщения поддержки',
    'role': 'Роли',
}


@login_required
@user_passes_test(admin_required, login_url='/login/')
def admin_panel_models(request):
    """Список всех доступных моделей для редактирования"""
    models_list = []
    for key, model_class in MODEL_MAP.items():
        count = model_class.objects.count()
        models_list.append({
            'key': key,
            'name': MODEL_NAMES.get(key, model_class.__name__),
            'count': count,
            'model': model_class,
        })
    
    context = {
        'models_list': models_list,
    }
    return render(request, 'admin_panel/models_list.html', context)


@login_required
@user_passes_test(admin_required, login_url='/login/')
def admin_panel_model_list(request, model_name):
    """Список объектов конкретной модели"""
    if model_name not in MODEL_MAP:
        messages.error(request, 'Модель не найдена')
        return redirect('admin_panel_models')
    
    model_class = MODEL_MAP[model_name]
    objects = model_class.objects.all()[:100]  # Ограничиваем для производительности
    
    # Получаем поля модели для отображения
    fields = [f.name for f in model_class._meta.get_fields() if not f.many_to_many and not f.one_to_many]
    
    # Подготавливаем данные для отображения
    objects_data = []
    for obj in objects:
        obj_data = {'id': obj.id, 'fields': {}}
        for field_name in fields[:8]:  # Первые 8 полей
            try:
                value = getattr(obj, field_name, None)
                if value is not None:
                    # Обрабатываем разные типы полей
                    if hasattr(value, '__str__'):
                        obj_data['fields'][field_name] = str(value)
                    else:
                        obj_data['fields'][field_name] = value
                else:
                    obj_data['fields'][field_name] = None
            except:
                obj_data['fields'][field_name] = None
        objects_data.append(obj_data)
    
    context = {
        'model_name': MODEL_NAMES.get(model_name, model_class.__name__),
        'model_key': model_name,
        'objects': objects,
        'objects_data': objects_data,
        'fields': fields[:8],  # Показываем первые 8 полей
        'count': model_class.objects.count(),
    }
    return render(request, 'admin_panel/model_list.html', context)


@login_required
@user_passes_test(admin_required, login_url='/login/')
def admin_panel_model_edit(request, model_name, object_id=None):
    """Редактирование или создание объекта модели"""
    """Редактирование или создание объекта модели"""
    if model_name not in MODEL_MAP:
        messages.error(request, 'Модель не найдена')
        return redirect('admin_panel_models')
    
    model_class = MODEL_MAP[model_name]
    
    # Получаем объект или создаем новый
    if object_id:
        obj = get_object_or_404(model_class, pk=object_id)
        is_new = False
    else:
        obj = model_class()
        is_new = True
    
    # Создаем форму динамически
    # Исключаем некоторые поля
    exclude_fields = ['id', 'created_at', 'updated_at']
    
    if hasattr(model_class, '_meta'):
        # Получаем только прямые поля модели (не обратные связи)
        # Используем _meta.fields для прямых полей и _meta.many_to_many для ManyToMany
        direct_fields = []
        
        # Прямые поля модели (ForeignKey, CharField, IntegerField и т.д.)
        for field in model_class._meta.fields:
            if field.name not in exclude_fields:
                direct_fields.append(field.name)
        
        # ManyToMany поля можно включить, но они требуют специальной обработки
        # Пока исключаем их, так как они сложны для редактирования
        # Можно добавить позже, если нужно
        
        form_fields = direct_fields if direct_fields else '__all__'
    else:
        form_fields = '__all__'
    
    # Создаем форму
    ModelForm = modelform_factory(
        model_class,
        fields=form_fields,
        exclude=exclude_fields
    )
    
    if request.method == 'POST':
        form = ModelForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            old_obj = None
            if not is_new:
                old_obj = model_class.objects.get(pk=obj.pk)
            
            form.save()
            
            # Логируем изменение
            action = 'create' if is_new else 'update'
            changes = {}
            if old_obj:
                for field in form.changed_data:
                    old_value = getattr(old_obj, field, None)
                    new_value = getattr(obj, field, None)
                    changes[field] = {
                        'old': str(old_value) if old_value is not None else '—',
                        'new': str(new_value) if new_value is not None else '—'
                    }
            
            log_action(
                action=action,
                user=request.user,
                request=request,
                model_name=model_class.__name__,
                object_id=obj.pk,
                object_repr=str(obj),
                changes=changes if changes else None,
            )
            
            messages.success(request, f'Объект успешно {"создан" if is_new else "обновлен"}!')
            return redirect('admin_panel_model_list', model_name=model_name)
    else:
        form = ModelForm(instance=obj)
    
    context = {
        'model_name': MODEL_NAMES.get(model_name, model_class.__name__),
        'model_key': model_name,
        'form': form,
        'object': obj,
        'is_new': is_new,
    }
    return render(request, 'admin_panel/model_edit.html', context)


def get_related_objects(obj):
    """
    Получает все связанные объекты через ForeignKey и ManyToMany
    Возвращает словарь с информацией о зависимостях
    """
    dependencies = {}
    
    # Проверяем обратные ForeignKey связи (когда другой объект ссылается на этот)
    # Это самый важный случай - когда удаляемый объект используется в других таблицах
    for related_object in obj._meta.related_objects:
        try:
            accessor_name = related_object.get_accessor_name()
            related_manager = getattr(obj, accessor_name)
            if hasattr(related_manager, 'all'):
                related_objects = related_manager.all()
                if related_objects.exists():
                    count = related_objects.count()
                    model = related_object.related_model
                    field = related_object.field
                    
                    dependencies[accessor_name] = {
                        'type': 'ReverseForeignKey',
                        'model': model.__name__,
                        'model_verbose': model._meta.verbose_name_plural or model.__name__,
                        'field_name': field.name if hasattr(field, 'name') else accessor_name,
                        'count': count,
                        'objects': list(related_objects[:10]),
                        'total': count,
                        'can_set_null': field.null if hasattr(field, 'null') else False,
                    }
        except (AttributeError, Exception) as e:
            # Игнорируем ошибки доступа
            pass
    
    # Проверяем ManyToMany связи (только для информации, они не блокируют удаление)
    for field in obj._meta.get_fields():
        if field.many_to_many and not field.auto_created:
            try:
                related_objects = getattr(obj, field.name).all()
                if related_objects.exists():
                    count = related_objects.count()
                    dependencies[f"m2m_{field.name}"] = {
                        'type': 'ManyToMany',
                        'model': field.related_model.__name__,
                        'model_verbose': field.related_model._meta.verbose_name_plural or field.related_model.__name__,
                        'field_name': field.name,
                        'count': count,
                        'objects': list(related_objects[:10]),
                        'total': count,
                        'can_set_null': True,  # M2M можно просто очистить
                    }
            except (AttributeError, Exception):
                pass
    
    return dependencies


@login_required
@user_passes_test(admin_required, login_url='/login/')
def admin_panel_model_delete(request, model_name, object_id):
    """Удаление объекта модели с проверкой зависимостей"""
    if model_name not in MODEL_MAP:
        messages.error(request, 'Модель не найдена')
        return redirect('admin_panel_models')
    
    model_class = MODEL_MAP[model_name]
    obj = get_object_or_404(model_class, pk=object_id)
    
    # Проверяем зависимости
    dependencies = get_related_objects(obj)
    
    if request.method == 'POST':
        # Если есть зависимости и пользователь не подтвердил принудительное удаление
        force_delete = request.POST.get('force_delete', 'false') == 'true'
        
        if dependencies and not force_delete:
            messages.error(request, 'Невозможно удалить объект: существуют связанные записи!')
            return redirect('admin_panel_model_delete', model_name=model_name, object_id=object_id)
        
        object_repr = str(obj)
        
        # Если принудительное удаление, удаляем связанные объекты или устанавливаем NULL
        if force_delete and dependencies:
            for dep_name, dep_info in dependencies.items():
                if dep_info['type'] == 'ReverseForeignKey':
                    # Удаляем связанные объекты или устанавливаем NULL
                    accessor = getattr(obj, dep_name)
                    for related_obj in accessor.all():
                        # Пытаемся установить NULL, если поле позволяет
                        if dep_info.get('can_set_null', False):
                            # Находим поле ForeignKey, которое ссылается на удаляемый объект
                            for field in related_obj._meta.get_fields():
                                if (field.many_to_one and 
                                    hasattr(field, 'related_model') and 
                                    field.related_model == model_class):
                                    setattr(related_obj, field.name, None)
                                    related_obj.save()
                                    break
                        else:
                            # Если нельзя установить NULL, удаляем связанный объект
                            related_obj.delete()
                elif dep_info['type'] == 'ManyToMany':
                    # Для M2M просто очищаем связи
                    field_name = dep_info.get('field_name', dep_name.replace('m2m_', ''))
                    getattr(obj, field_name).clear()
        
        obj.delete()
        
        # Логируем удаление
        log_action(
            action='delete',
            user=request.user,
            request=request,
            model_name=model_class.__name__,
            object_id=object_id,
            object_repr=object_repr,
        )
        
        messages.success(request, 'Объект успешно удален!')
        return redirect('admin_panel_model_list', model_name=model_name)
    
    context = {
        'model_name': MODEL_NAMES.get(model_name, model_class.__name__),
        'model_key': model_name,
        'object': obj,
        'dependencies': dependencies,
        'has_dependencies': bool(dependencies),
    }
    return render(request, 'admin_panel/model_delete.html', context)

