from decimal import Decimal
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, OperationalError, ProgrammingError


def cart_context(request):
    """Context processor для корзины - доступен во всех шаблонах"""
    cart = request.session.get("cart", {})
    total_quantity = 0
    
    for item in cart.values():
        total_quantity += item.get("quantity", 0)
    
    return {
        'cart_total_quantity': total_quantity,
    }


def wishlist_context(request):
    """Context processor для избранного - доступен во всех шаблонах"""
    wishlist_count = 0
    
    # Проверяем, существует ли таблица wishlist и пользователь авторизован
    if request.user.is_authenticated:
        try:
            # Пытаемся получить количество элементов избранного
            # Если таблица не существует, это вызовет ProgrammingError
            wishlist_count = request.user.wishlist_items.count()
        except (ProgrammingError, OperationalError):
            # Таблица еще не создана (миграции не применены)
            # Просто возвращаем 0, чтобы не ломать сайт
            wishlist_count = 0
        except Exception:
            # Любая другая ошибка - тоже возвращаем 0
            wishlist_count = 0
    
    return {
        'wishlist_count': wishlist_count,
    }


def categories_context(request):
    """Context processor для категорий - доступен во всех шаблонах"""
    from .models import Book, Genre, Author, Publisher
    
    try:
        books_count = Book.objects.count()
        genres_count = Genre.objects.count()
        authors_count = Author.objects.count()
        publishers_count = Publisher.objects.count()
    except (ProgrammingError, OperationalError):
        books_count = 0
        genres_count = 0
        authors_count = 0
        publishers_count = 0
    except Exception:
        books_count = 0
        genres_count = 0
        authors_count = 0
        publishers_count = 0
    
    return {
        'books_count': books_count,
        'genres_count': genres_count,
        'authors_count': authors_count,
        'publishers_count': publishers_count,
    }

