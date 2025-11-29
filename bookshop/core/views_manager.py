from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q, F, Max, Min
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
from decimal import Decimal
import csv
import json

from .models import (
    Order,
    OrderItem,
    Book,
    Stationery,
    User,
    Review,
    LoyaltyCard,
)
from .admin_utils import export_all_data_to_json, import_data_from_json
from .audit import log_action


def manager_required(user):
    """Проверка, что пользователь является менеджером или админом"""
    if not user.is_authenticated:
        return False
    # Админ имеет доступ ко всему
    if user.is_admin_method():
        return True
    # Менеджер имеет доступ к панели менеджера
    return user.is_manager_method()


def admin_required(user):
    """Проверка, что пользователь является админом"""
    if not user.is_authenticated:
        return False
    return user.is_admin_method()


def manager_only_required(user):
    """Проверка, что пользователь является только менеджером (не админом)"""
    if not user.is_authenticated:
        return False
    return user.is_manager_method() and not user.is_admin_method()


@login_required
@user_passes_test(manager_required, login_url='/login/')
def manager_dashboard(request):
    """Главная страница панели менеджера с дашбордом"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Статистика по заказам
    total_orders = Order.objects.count()
    today_orders = Order.objects.filter(created_at__date=today).count()
    week_orders = Order.objects.filter(created_at__date__gte=week_ago).count()
    month_orders = Order.objects.filter(created_at__date__gte=month_ago).count()
    
    # Статистика по продажам
    total_revenue = Order.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')
    
    today_revenue = Order.objects.filter(
        created_at__date=today
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')
    
    week_revenue = Order.objects.filter(
        created_at__date__gte=week_ago
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')
    
    month_revenue = Order.objects.filter(
        created_at__date__gte=month_ago
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0.00')
    
    # Статистика по товарам
    total_books = Book.objects.count()
    total_stationery = Stationery.objects.count()
    low_stock_books = Book.objects.filter(stock_quantity__lte=5).count()
    low_stock_stationery = Stationery.objects.filter(stock_quantity__lte=5).count()
    
    # Статистика по пользователям
    total_users = User.objects.count()
    total_loyalty_cards = LoyaltyCard.objects.count()
    total_reviews = Review.objects.count()
    
    # Заказы по статусам
    orders_by_status = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Последние заказы
    recent_orders = Order.objects.select_related(
        'user', 'delivery_option', 'pickup_point'
    ).prefetch_related('items')[:10]
    
    # Топ товаров (по количеству продаж)
    # Получаем все OrderItems с книгами
    book_items = OrderItem.objects.filter(product_type='book').values('product_id').annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:5]
    
    top_books = []
    for item in book_items:
        try:
            book = Book.objects.get(pk=item['product_id'])
            book.total_sold = item['total_sold'] or 0
            top_books.append(book)
        except Book.DoesNotExist:
            pass
    
    # Аналогично для канцтоваров
    stationery_items = OrderItem.objects.filter(product_type='stationery').values('product_id').annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:5]
    
    top_stationery = []
    for item in stationery_items:
        try:
            stationery = Stationery.objects.get(pk=item['product_id'])
            stationery.total_sold = item['total_sold'] or 0
            top_stationery.append(stationery)
        except Stationery.DoesNotExist:
            pass
    
    context = {
        'total_orders': total_orders,
        'today_orders': today_orders,
        'week_orders': week_orders,
        'month_orders': month_orders,
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'total_books': total_books,
        'total_stationery': total_stationery,
        'low_stock_books': low_stock_books,
        'low_stock_stationery': low_stock_stationery,
        'total_users': total_users,
        'total_loyalty_cards': total_loyalty_cards,
        'total_reviews': total_reviews,
        'orders_by_status': orders_by_status,
        'recent_orders': recent_orders,
        'top_books': top_books,
        'top_stationery': top_stationery,
    }
    return render(request, 'manager/dashboard.html', context)


@login_required
@user_passes_test(manager_required, login_url='/login/')
def manager_orders(request):
    """Список всех заказов"""
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    orders = Order.objects.select_related(
        'user', 'delivery_option', 'pickup_point'
    ).prefetch_related('items').order_by('-created_at')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if search_query:
        # Попытка найти по ID если это число
        try:
            order_id = int(search_query)
            orders = Order.objects.filter(
                Q(pk=order_id) |
                Q(full_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            ).select_related(
                'user', 'delivery_option', 'pickup_point'
            ).prefetch_related('items').order_by('-created_at')
        except ValueError:
            orders = orders.filter(
                Q(full_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
    
    context = {
        'orders': orders,
        'status_filter': status_filter,
        'search_query': search_query,
        'status_choices': Order.Status.choices,
    }
    return render(request, 'manager/orders.html', context)


@login_required
@user_passes_test(manager_required, login_url='/login/')
def manager_order_detail(request, order_id):
    """Детали заказа"""
    order = get_object_or_404(
        Order.objects.select_related('user', 'delivery_option', 'pickup_point').prefetch_related('items'),
        pk=order_id
    )
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in [choice[0] for choice in Order.Status.choices]:
            order.status = new_status
            order.save()
            messages.success(request, f'Статус заказа #{order.id} изменен на "{order.get_status_display()}"')
            return redirect('manager_order_detail', order_id=order.id)
    
    context = {
        'order': order,
        'status_choices': Order.Status.choices,
    }
    return render(request, 'manager/order_detail.html', context)


@login_required
@user_passes_test(admin_required, login_url='/login/')
def manager_products(request):
    """Управление товарами"""
    product_type = request.GET.get('type', 'books')
    
    if product_type == 'stationery':
        products = Stationery.objects.select_related('category').order_by('-id')
        low_stock = Stationery.objects.filter(stock_quantity__lte=5).count()
        total_books = Book.objects.count()
        total_stationery = Stationery.objects.count()
    else:
        products = Book.objects.select_related('publisher').prefetch_related('authors', 'genres').order_by('-id')
        low_stock = Book.objects.filter(stock_quantity__lte=5).count()
        total_books = Book.objects.count()
        total_stationery = Stationery.objects.count()
    
    context = {
        'products': products,
        'product_type': product_type,
        'low_stock': low_stock,
        'total_books': total_books,
        'total_stationery': total_stationery,
    }
    return render(request, 'manager/products.html', context)


@login_required
@user_passes_test(manager_required, login_url='/login/')
def manager_statistics(request):
    """Статистика с данными по заказам и клиентам"""
    # Выбор периода
    period = request.GET.get('period', 'month')  # week, month, year
    today = timezone.now().date()
    
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:  # month
        start_date = today - timedelta(days=30)
    
    # Базовый queryset заказов за период
    orders = Order.objects.filter(created_at__date__gte=start_date)
    
    # Статистика продаж по дням
    daily_sales = orders.annotate(
        day=TruncDate('created_at')
    ).values('day').annotate(
        revenue=Sum('total_amount'),
        count=Count('id')
    ).order_by('day')
    
    # Статистика по статусам заказов
    status_stats = orders.values('status').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('status')
    
    # Статистика по способам доставки
    delivery_stats = orders.values('fulfillment_type').annotate(
        count=Count('id')
    ).order_by('fulfillment_type')
    
    # Статистика по клиентам
    total_customers = orders.filter(user__isnull=False).values('user').distinct().count()
    total_guest_customers = orders.filter(user__isnull=True).values('email').distinct().count()
    total_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    avg_order_value = orders.aggregate(Avg('total_amount'))['total_amount__avg'] or Decimal('0')
    
    # Новые клиенты (первый заказ в периоде)
    new_customers = orders.filter(user__isnull=False).values('user').annotate(
        first_order=Min('created_at')
    ).filter(first_order__gte=start_date).count()
    
    # Топ клиентов (авторизованные)
    customer_stats = orders.filter(user__isnull=False).select_related('user').values(
        'user__id', 'user__email', 'user__first_name', 'user__last_name'
    ).annotate(
        total_orders=Count('id'),
        total_spent=Sum('total_amount'),
        avg_order_value=Avg('total_amount'),
        last_order_date=Max('created_at')
    ).order_by('-total_spent')[:20]
    
    # Топ гостевых клиентов
    guest_stats = orders.filter(user__isnull=True).values('email').annotate(
        total_orders=Count('id'),
        total_spent=Sum('total_amount'),
        avg_order_value=Avg('total_amount'),
        last_order_date=Max('created_at')
    ).order_by('-total_spent')[:10]
    
    context = {
        'period': period,
        'start_date': start_date,
        'end_date': today,
        'daily_sales': daily_sales,
        'status_stats': status_stats,
        'delivery_stats': delivery_stats,
        # Данные по клиентам
        'total_customers': total_customers,
        'total_guest_customers': total_guest_customers,
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        'new_customers': new_customers,
        'customer_stats': customer_stats,
        'guest_stats': guest_stats,
        # Данные по клиентам
        'total_customers': total_customers,
        'total_guest_customers': total_guest_customers,
        'total_revenue': total_revenue,
        'avg_order_value': avg_order_value,
        'new_customers': new_customers,
        'customer_stats': customer_stats,
        'guest_stats': guest_stats,
    }
    return render(request, 'manager/statistics.html', context)


@login_required
@user_passes_test(admin_required, login_url='/login/')
def manager_users(request):
    """Управление пользователями"""
    search_query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    
    users = User.objects.select_related('role').order_by('-id')
    
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    if role_filter:
        if role_filter == 'staff':
            users = users.filter(is_staff=True)
        elif role_filter == 'active':
            users = users.filter(is_active=True)
    
    context = {
        'users': users,
        'search_query': search_query,
        'role_filter': role_filter,
    }
    return render(request, 'manager/users.html', context)


@login_required
@user_passes_test(admin_required, login_url='/login/')
def manager_export_data(request):
    """Экспорт всех данных в JSON"""
    try:
        json_data = export_all_data_to_json()
        response = HttpResponse(json_data, content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="lexicon_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
        
        # Логируем экспорт данных
        log_action(
            action='export',
            user=request.user,
            request=request,
            description='Экспорт всех данных в JSON',
        )
        
        return response
    except Exception as e:
        messages.error(request, f"Ошибка при экспорте данных: {str(e)}")
        return redirect('manager_dashboard')


@login_required
@user_passes_test(admin_required, login_url='/login/')
@require_http_methods(["GET", "POST"])
def manager_import_data(request):
    """Импорт данных из JSON"""
    if request.method == 'GET':
        return render(request, 'manager/import_data.html')
    
    if 'json_file' not in request.FILES:
        messages.error(request, "Файл не выбран")
        return redirect('manager_import_data')
    
    json_file = request.FILES['json_file']
    
    try:
        json_data = json_file.read().decode('utf-8')
        result = import_data_from_json(json_data)
        
        # Логируем импорт данных
        log_action(
            action='import',
            user=request.user,
            request=request,
            description=f'Импорт данных из файла: {json_file.name}',
        )
        
        # Формируем сообщение о результате
        total_imported = sum(result.get('imported', {}).values())
        if result.get('errors'):
            messages.warning(
                request, 
                f"Импорт завершен с предупреждениями. Импортировано записей: {total_imported}. "
                f"Ошибок: {len(result['errors'])}"
            )
        else:
            messages.success(request, f"Данные успешно импортированы. Импортировано записей: {total_imported}")
    except ValueError as e:
        messages.error(request, f"Ошибка при импорте данных: {str(e)}")
    except Exception as e:
        messages.error(request, f"Неожиданная ошибка при импорте данных: {str(e)}")
    
    return redirect('manager_import_data')


@login_required
@user_passes_test(manager_required, login_url='/login/')
def manager_reports(request):
    """Страница с отчетами (объединенная - заказы и клиенты)"""
    # Получаем параметры фильтров для заказов
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
    
    # Статистика по заказам
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
    
    # Данные по клиентам (для второй вкладки)
    orders_for_customers = Order.objects.select_related('user').all()
    
    # Применяем те же фильтры по дате
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            orders_for_customers = orders_for_customers.filter(created_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_obj = date_to_obj + timedelta(days=1)
            orders_for_customers = orders_for_customers.filter(created_at__lt=date_to_obj)
        except ValueError:
            pass
    
    if not date_from and not date_to:
        month_ago = timezone.now() - timedelta(days=30)
        orders_for_customers = orders_for_customers.filter(created_at__gte=month_ago)
    
    # Статистика по клиентам
    customer_stats = orders_for_customers.filter(user__isnull=False).values(
        'user__id', 'user__email', 'user__first_name', 'user__last_name'
    ).annotate(
        total_orders=Count('id'),
        total_spent=Sum('total_amount'),
        avg_order_value=Avg('total_amount'),
        last_order_date=Max('created_at')
    ).order_by('-total_spent')[:20]
    
    guest_stats = orders_for_customers.filter(user__isnull=True).values('email').annotate(
        total_orders=Count('id'),
        total_spent=Sum('total_amount'),
        avg_order_value=Avg('total_amount'),
        last_order_date=Max('created_at')
    ).order_by('-total_spent')[:10]
    
    total_customers = orders_for_customers.filter(user__isnull=False).values('user').distinct().count()
    total_guest_customers = orders_for_customers.filter(user__isnull=True).values('email').distinct().count()
    
    if date_from or date_to:
        start_date_obj = datetime.strptime(date_from, '%Y-%m-%d').date() if date_from else (timezone.now() - timedelta(days=30)).date()
        new_customers = orders_for_customers.filter(user__isnull=False).values('user').annotate(
            first_order=Min('created_at')
        ).filter(first_order__date__gte=start_date_obj).count()
    else:
        month_ago = timezone.now() - timedelta(days=30)
        new_customers = orders_for_customers.filter(
            user__isnull=False,
            created_at__gte=month_ago
        ).values('user').annotate(
            first_order=Min('created_at')
        ).filter(first_order__gte=month_ago).count()
    
    context = {
        # Данные по заказам
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
        # Данные по клиентам
        'customer_stats': customer_stats,
        'guest_stats': guest_stats,
        'total_customers': total_customers,
        'total_guest_customers': total_guest_customers,
        'new_customers': new_customers,
    }
    
    return render(request, 'manager/reports.html', context)


@login_required
@user_passes_test(manager_required, login_url='/login/')
def manager_reports_export_csv(request):
    """Экспорт отчета в CSV"""
    # Логируем скачивание отчета
    log_action(
        action='download',
        user=request.user,
        request=request,
        description='Скачивание отчета в формате CSV',
    )
    
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


@login_required
@user_passes_test(manager_required, login_url='/login/')
def manager_reports_export_image(request):
    """Экспорт отчета в виде изображения (PNG)"""
    # Логируем скачивание отчета
    log_action(
        action='download',
        user=request.user,
        request=request,
        description='Скачивание отчета в формате PNG',
    )
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from io import BytesIO
    except ImportError:
        messages.error(request, "Библиотека matplotlib не установлена. Установите: pip install matplotlib")
        return redirect('manager_reports')
    
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
    
    ax1.plot(days, counts, marker='o', linewidth=2, markersize=6, color='#6F2DBD')
    ax1.set_title('Количество заказов по дням', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Дата')
    ax1.set_ylabel('Количество заказов')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # График выручки
    revenues = [float(stat['revenue'] or 0) for stat in daily_stats]
    ax2.plot(days, revenues, marker='o', color='#A663CC', linewidth=2, markersize=6)
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


@login_required
@user_passes_test(manager_required, login_url='/login/')
def manager_reports_customers(request):
    """Отчет по клиентам (покупателям)"""
    # Получаем параметры фильтров
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Базовый queryset заказов
    orders = Order.objects.select_related('user').all()
    
    # Применяем фильтры по дате
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
    
    # Если фильтры не заданы, показываем данные за последний месяц
    if not date_from and not date_to:
        month_ago = timezone.now() - timedelta(days=30)
        orders = orders.filter(created_at__gte=month_ago)
    
    # Статистика по авторизованным клиентам
    customer_stats = orders.filter(user__isnull=False).values(
        'user__id', 'user__email', 'user__first_name', 'user__last_name'
    ).annotate(
        total_orders=Count('id'),
        total_spent=Sum('total_amount'),
        avg_order_value=Avg('total_amount'),
        last_order_date=Max('created_at')
    ).order_by('-total_spent')[:20]
    
    # Статистика по неавторизованным клиентам (по email)
    guest_stats = orders.filter(user__isnull=True).values('email').annotate(
        total_orders=Count('id'),
        total_spent=Sum('total_amount'),
        avg_order_value=Avg('total_amount'),
        last_order_date=Max('created_at')
    ).order_by('-total_spent')[:10]
    
    # Общая статистика
    total_customers = orders.filter(user__isnull=False).values('user').distinct().count()
    total_guest_customers = orders.filter(user__isnull=True).values('email').distinct().count()
    total_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    
    # Статистика по новым клиентам (первый заказ в периоде)
    if date_from or date_to:
        # Если есть фильтр по дате, считаем новых клиентов в этом периоде
        new_customers = orders.filter(user__isnull=False).values('user').annotate(
            first_order=Min('created_at')
        ).filter(first_order__gte=orders.aggregate(Min('created_at'))['created_at__min']).count()
    else:
        # За последний месяц
        month_ago = timezone.now() - timedelta(days=30)
        new_customers = orders.filter(
            user__isnull=False,
            created_at__gte=month_ago
        ).values('user').annotate(
            first_order=Min('created_at')
        ).filter(first_order__gte=month_ago).count()
    
    # Статистика по среднему чеку
    avg_order_value = orders.aggregate(Avg('total_amount'))['total_amount__avg'] or Decimal('0')
    
    context = {
        'customer_stats': customer_stats,
        'guest_stats': guest_stats,
        'total_customers': total_customers,
        'total_guest_customers': total_guest_customers,
        'total_revenue': total_revenue,
        'new_customers': new_customers,
        'avg_order_value': avg_order_value,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'manager/reports_customers.html', context)


@login_required
@user_passes_test(manager_required, login_url='/login/')
def manager_reports_customers_export_csv(request):
    """Экспорт отчета по клиентам в CSV"""
    log_action(
        action='download',
        user=request.user,
        request=request,
        description='Скачивание отчета по клиентам в формате CSV',
    )
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    orders = Order.objects.select_related('user').all()
    
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
    
    if not date_from and not date_to:
        month_ago = timezone.now() - timedelta(days=30)
        orders = orders.filter(created_at__gte=month_ago)
    
    customer_stats = orders.filter(user__isnull=False).values(
        'user__id', 'user__email', 'user__first_name', 'user__last_name'
    ).annotate(
        total_orders=Count('id'),
        total_spent=Sum('total_amount'),
        avg_order_value=Avg('total_amount'),
        last_order_date=Max('created_at')
    ).order_by('-total_spent')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="lexicon_customers_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID клиента', 'Email', 'Имя', 'Фамилия', 'Количество заказов',
        'Общая сумма', 'Средний чек', 'Последний заказ'
    ])
    
    for stat in customer_stats:
        writer.writerow([
            stat['user__id'],
            stat['user__email'],
            stat['user__first_name'] or '',
            stat['user__last_name'] or '',
            stat['total_orders'],
            str(stat['total_spent']),
            str(stat['avg_order_value']),
            stat['last_order_date'].strftime('%Y-%m-%d %H:%M:%S') if stat['last_order_date'] else '',
        ])
    
    return response


@login_required
@user_passes_test(manager_required, login_url='/login/')
def manager_reports_customers_export_image(request):
    """Экспорт отчета по клиентам в виде изображения (PNG)"""
    log_action(
        action='download',
        user=request.user,
        request=request,
        description='Скачивание отчета по клиентам в формате PNG',
    )
    
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from io import BytesIO
    except ImportError:
        messages.error(request, "Библиотека matplotlib не установлена. Установите: pip install matplotlib")
        return redirect('manager_reports_customers')
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    orders = Order.objects.select_related('user').all()
    
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
    
    if not date_from and not date_to:
        month_ago = timezone.now() - timedelta(days=30)
        orders = orders.filter(created_at__gte=month_ago)
    
    customer_stats = orders.filter(user__isnull=False).values(
        'user__email'
    ).annotate(
        total_spent=Sum('total_amount')
    ).order_by('-total_spent')[:10]
    
    # Создаем график
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # График топ-10 клиентов по сумме покупок
    emails = [stat['user__email'][:20] + '...' if len(stat['user__email']) > 20 else stat['user__email'] for stat in customer_stats]
    amounts = [float(stat['total_spent'] or 0) for stat in customer_stats]
    
    ax1.barh(emails, amounts, color='#6F2DBD')
    ax1.set_title('Топ-10 клиентов по сумме покупок', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Сумма покупок (руб.)')
    ax1.grid(True, alpha=0.3, axis='x')
    
    # Круговая диаграмма: авторизованные vs гостевые клиенты
    auth_count = orders.filter(user__isnull=False).values('user').distinct().count()
    guest_count = orders.filter(user__isnull=True).values('email').distinct().count()
    
    if auth_count > 0 or guest_count > 0:
        ax2.pie([auth_count, guest_count], labels=['Авторизованные', 'Гостевые'], 
                autopct='%1.1f%%', colors=['#6F2DBD', '#A663CC'], startangle=90)
        ax2.set_title('Распределение клиентов', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    buffer = BytesIO()
    canvas = FigureCanvasAgg(fig)
    canvas.print_png(buffer)
    plt.close(fig)
    
    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="lexicon_customers_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png"'
    
    return response


@login_required
@user_passes_test(admin_required, login_url='/login/')
def manager_audit_log(request):
    """Журнал аудита - отслеживание изменений"""
    from .models import AuditLog
    
    # Фильтры
    model_filter = request.GET.get('model', '')
    action_filter = request.GET.get('action', '')
    user_filter = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search_query = request.GET.get('q', '')
    
    # Базовый queryset
    audit_logs = AuditLog.objects.select_related('user').all()
    
    # Применяем фильтры
    if model_filter:
        audit_logs = audit_logs.filter(model_name=model_filter)
    
    if action_filter:
        audit_logs = audit_logs.filter(action=action_filter)
    
    if user_filter:
        try:
            user_id = int(user_filter)
            audit_logs = audit_logs.filter(user_id=user_id)
        except ValueError:
            pass
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            audit_logs = audit_logs.filter(created_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_obj = date_to_obj + timedelta(days=1)
            audit_logs = audit_logs.filter(created_at__lt=date_to_obj)
        except ValueError:
            pass
    
    if search_query:
        audit_logs = audit_logs.filter(
            Q(object_repr__icontains=search_query) |
            Q(model_name__icontains=search_query)
        )
    
    # Если фильтры не заданы, показываем за последние 7 дней
    if not date_from and not date_to:
        week_ago = timezone.now() - timedelta(days=7)
        audit_logs = audit_logs.filter(created_at__gte=week_ago)
    
    # Статистика
    total_logs = audit_logs.count()
    stats_by_action = audit_logs.values('action').annotate(count=Count('id')).order_by('-count')
    stats_by_model = audit_logs.values('model_name').annotate(count=Count('id')).order_by('-count')
    
    # Получаем уникальные модели для фильтра
    all_models = AuditLog.objects.values_list('model_name', flat=True).distinct().order_by('model_name')
    
    # Получаем пользователей, которые вносили изменения
    users_with_changes = User.objects.filter(
        id__in=AuditLog.objects.values_list('user_id', flat=True).distinct()
    ).order_by('email')
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(audit_logs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'audit_logs': page_obj,
        'total_logs': total_logs,
        'stats_by_action': stats_by_action,
        'stats_by_model': stats_by_model,
        'all_models': all_models,
        'users_with_changes': users_with_changes,
        'model_filter': model_filter,
        'action_filter': action_filter,
        'user_filter': user_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        'action_choices': AuditLog.ACTION_TYPES,
    }
    
    return render(request, 'manager/audit_log.html', context)


@login_required
@user_passes_test(admin_required, login_url='/login/')
def manager_audit_log_details(request, log_id):
    """Детали записи аудита (AJAX)"""
    from .models import AuditLog
    
    log = get_object_or_404(AuditLog, pk=log_id)
    
    return render(request, 'manager/audit_log_details.html', {'log': log})

