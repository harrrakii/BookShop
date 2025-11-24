from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Book, Stationery, Wishlist
from .audit import log_action


@login_required
@require_POST
def toggle_wishlist(request, product_type: str, pk: int):
    """Добавляет или удаляет товар из избранного"""
    from django.db import ProgrammingError, OperationalError
    
    user = request.user
    
    try:
        if product_type == 'book':
            product = get_object_or_404(Book, pk=pk)
            wishlist_item, created = Wishlist.objects.get_or_create(
                user=user,
                book=product
            )
            product_name = product.title
        elif product_type == 'stationery':
            product = get_object_or_404(Stationery, pk=pk)
            wishlist_item, created = Wishlist.objects.get_or_create(
                user=user,
                stationery=product
            )
            product_name = product.name
        else:
            messages.error(request, 'Неверный тип товара')
            return redirect('home')
        
        if not created:
            # Товар уже в избранном, удаляем
            wishlist_item.delete()
            action_text = 'удален из'
            is_in_wishlist = False
        else:
            # Товар добавлен в избранное
            action_text = 'добавлен в'
            is_in_wishlist = True
            
            log_action(
                action='create',
                user=user,
                request=request,
                model_name='Wishlist',
                object_id=wishlist_item.id,
                object_repr=f'{user.email} - {product_name}',
                description=f'Товар "{product_name}" добавлен в избранное',
            )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # AJAX запрос
            wishlist_count = Wishlist.objects.filter(user=user).count()
            return JsonResponse({
                'success': True,
                'is_in_wishlist': is_in_wishlist,
                'wishlist_count': wishlist_count,
                'message': f'Товар "{product_name}" {action_text} избранное'
            })
        
        messages.success(request, f'Товар "{product_name}" {action_text} избранное')
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("wishlist_view")
        return redirect(next_url)
    except (ProgrammingError, OperationalError):
        messages.error(request, 'Функция избранного временно недоступна. Пожалуйста, примените миграции базы данных.')
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("home")
        return redirect(next_url)


@login_required
def wishlist_view(request):
    """Страница избранного"""
    from django.db import ProgrammingError, OperationalError
    
    try:
        wishlist_items = Wishlist.objects.filter(user=request.user).select_related('book', 'stationery')
        
        # Разделяем на книги и канцтовары
        books = []
        stationery_items = []
        
        for item in wishlist_items:
            if item.book:
                books.append(item.book)
            elif item.stationery:
                stationery_items.append(item.stationery)
        
        log_action(
            action='view',
            user=request.user,
            request=request,
            model_name='Wishlist',
            object_id=None,
            object_repr='Список избранного',
            description='Просмотр страницы избранного',
        )
        
        context = {
            'wishlist_items': wishlist_items,
            'books': books,
            'stationery_items': stationery_items,
        }
    except (ProgrammingError, OperationalError) as e:
        # Таблица еще не создана - показываем пустое избранное
        from django.contrib import messages
        messages.info(request, 'Функция избранного будет доступна после применения миграций базы данных.')
        context = {
            'wishlist_items': [],
            'books': [],
            'stationery_items': [],
        }
    
    return render(request, 'wishlist.html', context)


@login_required
def check_wishlist_status(request, product_type: str, pk: int):
    """Проверяет, находится ли товар в избранном (для AJAX)"""
    from django.db import ProgrammingError, OperationalError
    
    if not request.user.is_authenticated:
        return JsonResponse({'is_in_wishlist': False})
    
    try:
        if product_type == 'book':
            is_in_wishlist = Wishlist.objects.filter(user=request.user, book_id=pk).exists()
        elif product_type == 'stationery':
            is_in_wishlist = Wishlist.objects.filter(user=request.user, stationery_id=pk).exists()
        else:
            return JsonResponse({'error': 'Неверный тип товара'}, status=400)
        
        return JsonResponse({'is_in_wishlist': is_in_wishlist})
    except (ProgrammingError, OperationalError):
        # Таблица не существует
        return JsonResponse({'is_in_wishlist': False})

