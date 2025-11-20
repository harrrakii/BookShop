"""
Views для админки: экспорт/импорт и отчеты
"""
import csv
import json
import io
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Order, OrderItem, Book, User, Product, Review
from .admin_utils import export_all_data_to_json, import_data_from_json


@staff_member_required
def admin_export_data(request):
    """Экспорт всех данных в JSON"""
    try:
        json_data = export_all_data_to_json()
        response = HttpResponse(json_data, content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="lexicon_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        return response
    except Exception as e:
        messages.error(request, f"Ошибка при экспорте данных: {str(e)}")
        return redirect('admin:index')


@staff_member_required
@require_http_methods(["GET", "POST"])
def admin_import_data(request):
    """Импорт данных из JSON"""
    if request.method == 'GET':
        return render(request, 'admin/import_data.html')
    
    if 'json_file' not in request.FILES:
        messages.error(request, "Файл не выбран")
        return redirect('admin:index')
    
    json_file = request.FILES['json_file']
    
    try:
        json_data = json_file.read().decode('utf-8')
        import_data_from_json(json_data)
        messages.success(request, "Данные успешно импортированы")
    except Exception as e:
        messages.error(request, f"Ошибка при импорте данных: {str(e)}")
    
    return redirect('admin:index')


@staff_member_required
def admin_reports(request):
    """Страница с отчетами"""
    # Получаем параметры фильтров
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status = request.GET.get('status', '')
    fulfillment_type = request.GET.get('fulfillment_type', '')
    
    # Базовый queryset заказов
    orders = Order.objects.all()
    
    # Применяем фильтры
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            orders = orders.filter(created_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Добавляем 1 день, чтобы включить весь день
            date_to_obj = date_to_obj + timedelta(days=1)
            orders = orders.filter(created_at__lt=date_to_obj)
        except ValueError:
            pass
    
    if status:
        orders = orders.filter(status=status)
    
    if fulfillment_type:
        orders = orders.filter(fulfillment_type=fulfillment_type)
    
    # Если фильтры не заданы, показываем данные за последний месяц
    if not date_from and not date_to:
        month_ago = timezone.now() - timedelta(days=30)
        orders = orders.filter(created_at__gte=month_ago)
    
    # Статистика
    total_orders = orders.count()
    total_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    avg_order_value = orders.aggregate(Avg('total_amount'))['total_amount__avg'] or Decimal('0')
    
    # Статистика по статусам
    status_stats = orders.values('status').annotate(count=Count('id')).order_by('-count')
    
    # Статистика по типам доставки
    fulfillment_stats = orders.values('fulfillment_type').annotate(count=Count('id')).order_by('-count')
    
    # Топ товаров
    top_products = OrderItem.objects.filter(order__in=orders).values(
        'product_type', 'product_id', 'name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('subtotal')
    ).order_by('-total_quantity')[:10]
    
    # Статистика по дням
    daily_stats = orders.extra(
        select={'day': "DATE(created_at)"}
    ).values('day').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('day')
    
    context = {
        'orders': orders[:100],  # Ограничиваем для отображения
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        'status_stats': status_stats,
        'fulfillment_stats': fulfillment_stats,
        'top_products': top_products,
        'daily_stats': daily_stats,
        'date_from': date_from,
        'date_to': date_to,
        'status': status,
        'fulfillment_type': fulfillment_type,
        'status_choices': Order.Status.choices,
        'fulfillment_choices': Order.FulfillmentType.choices,
    }
    
    return render(request, 'admin/reports.html', context)


@staff_member_required
def admin_reports_export_csv(request):
    """Экспорт отчета в CSV"""
    # Получаем те же фильтры, что и в отчете
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status = request.GET.get('status', '')
    fulfillment_type = request.GET.get('fulfillment_type', '')
    
    orders = Order.objects.all()
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            orders = orders.filter(created_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_obj = date_to_obj + timedelta(days=1)
            orders = orders.filter(created_at__lt=date_to_obj)
        except ValueError:
            pass
    
    if status:
        orders = orders.filter(status=status)
    
    if fulfillment_type:
        orders = orders.filter(fulfillment_type=fulfillment_type)
    
    # Создаем CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="lexicon_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID заказа', 'Дата', 'Клиент', 'Email', 'Телефон',
        'Тип доставки', 'Статус', 'Сумма', 'Количество товаров'
    ])
    
    for order in orders:
        items_count = order.items.count()
        writer.writerow([
            order.id,
            order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            order.full_name,
            order.email,
            order.phone,
            order.get_fulfillment_type_display(),
            order.get_status_display(),
            str(order.total_amount),
            items_count,
        ])
    
    return response


@staff_member_required
def admin_reports_export_image(request):
    """Экспорт отчета в виде изображения (PNG)"""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Используем backend без GUI
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from io import BytesIO
    except ImportError:
        messages.error(request, "Библиотека matplotlib не установлена. Установите: pip install matplotlib")
        return redirect('admin_reports')
    
    # Получаем фильтры
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status = request.GET.get('status', '')
    fulfillment_type = request.GET.get('fulfillment_type', '')
    
    orders = Order.objects.all()
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            orders = orders.filter(created_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_obj = date_to_obj + timedelta(days=1)
            orders = orders.filter(created_at__lt=date_to_obj)
        except ValueError:
            pass
    
    if status:
        orders = orders.filter(status=status)
    
    if fulfillment_type:
        orders = orders.filter(fulfillment_type=fulfillment_type)
    
    # Статистика по дням
    daily_stats = orders.extra(
        select={'day': "DATE(created_at)"}
    ).values('day').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('day')
    
    # Создаем график
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # График количества заказов
    days = [stat['day'] for stat in daily_stats]
    counts = [stat['count'] for stat in daily_stats]
    
    ax1.plot(days, counts, marker='o', linewidth=2, markersize=6)
    ax1.set_title('Количество заказов по дням', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Дата')
    ax1.set_ylabel('Количество заказов')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # График выручки
    revenues = [float(stat['revenue'] or 0) for stat in daily_stats]
    ax2.plot(days, revenues, marker='o', color='green', linewidth=2, markersize=6)
    ax2.set_title('Выручка по дням', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Дата')
    ax2.set_ylabel('Выручка (руб.)')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    # Сохраняем в BytesIO
    buffer = BytesIO()
    canvas = FigureCanvasAgg(fig)
    canvas.print_png(buffer)
    plt.close(fig)
    
    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="lexicon_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png"'
    
    return response

