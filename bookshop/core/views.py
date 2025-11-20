from decimal import Decimal

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from rest_framework import viewsets

from .models import (
    Category,
    Publisher,
    Book,
    Stationery,
    Product,
    Author,
    Genre,
    Order,
    OrderItem,
    Review,
    SavedAddress,
    PaymentCard,
    LoyaltyCard,
)
from django.db.models import Count

from .forms import CheckoutForm
from .audit import log_action
from .serializers import (
    CategorySerializer,
    PublisherSerializer,
    BookSerializer,
    StationerySerializer,
    ProductSerializer,
    AuthorSerializer,
    GenreSerializer,
)


# ---------- DRF ViewSets (API) ----------

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class PublisherViewSet(viewsets.ModelViewSet):
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer


class StationeryViewSet(viewsets.ModelViewSet):
    queryset = Stationery.objects.all()
    serializer_class = StationerySerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


# ---------- Обычные HTML-views ----------

def home(request):
    return render(request, "index.html")


def books_list(request):
    """Главная страница каталога книг с выбором фильтра"""
    # Получаем все жанры, авторы и издатели для меню
    genres = Genre.objects.all().annotate(
        books_count=Count('books')
    ).order_by('name')
    authors = Author.objects.all().annotate(
        books_count=Count('books')
    ).order_by('last_name', 'first_name')
    publishers = Publisher.objects.all().annotate(
        books_count=Count('books')
    ).order_by('name')
    
    # Получаем все книги для страницы "Все книги"
    books = Book.objects.select_related("publisher").prefetch_related("authors", "genres").all()
    
    # Параметры сортировки
    sort_by = request.GET.get('sort', 'rating')  # rating, year
    order = request.GET.get('order', 'desc')  # asc, desc
    
    # Применяем сортировку
    if sort_by == 'year':
        if order == 'desc':
            books = books.order_by('-publication_year', 'title')
        else:
            books = books.order_by('publication_year', 'title')
    else:  # sort_by == 'rating' (по умолчанию)
        if order == 'desc':
            books = books.order_by('-rating', 'title')
        else:
            books = books.order_by('rating', 'title')
    
    context = {
        'books': books,
        'genres': genres,
        'authors': authors,
        'publishers': publishers,
        'sort_by': sort_by,
        'order': order,
        'filter_type': 'all',  # all, genre, author, publisher
    }
    return render(request, "books_list.html", context)


def books_by_genre(request, genre_id):
    """Страница книг по жанру"""
    genre = get_object_or_404(Genre, pk=genre_id)
    
    # Параметры сортировки
    sort_by = request.GET.get('sort', 'rating')
    order = request.GET.get('order', 'desc')
    
    books = Book.objects.filter(genres=genre).select_related("publisher").prefetch_related("authors", "genres")
    
    # Применяем сортировку
    if sort_by == 'year':
        if order == 'desc':
            books = books.order_by('-publication_year', 'title')
        else:
            books = books.order_by('publication_year', 'title')
    else:  # sort_by == 'rating' (по умолчанию)
        if order == 'desc':
            books = books.order_by('-rating', 'title')
        else:
            books = books.order_by('rating', 'title')
    
    context = {
        'books': books,
        'genre': genre,
        'sort_by': sort_by,
        'order': order,
        'filter_type': 'genre',
    }
    return render(request, "books_filtered.html", context)


def author_detail(request, author_id):
    """Страница с подробной информацией об авторе"""
    author = get_object_or_404(Author.objects.prefetch_related('books'), pk=author_id)
    
    # Получаем все книги автора с рейтингами
    books = author.books.all().select_related('publisher').prefetch_related('genres').order_by('-rating', 'title')
    
    # Логируем просмотр автора
    log_action(
        action='view',
        user=request.user if request.user.is_authenticated else None,
        request=request,
        model_name='Author',
        object_id=author.id,
        object_repr=str(author),
        description=f'Просмотр страницы автора: {author}',
    )
    
    context = {
        'author': author,
        'books': books,
    }
    return render(request, 'author_detail.html', context)


def books_by_author(request, author_id):
    """Страница книг по автору (старая версия - для совместимости)"""
    author = get_object_or_404(Author, pk=author_id)
    
    # Параметры сортировки
    sort_by = request.GET.get('sort', 'rating')
    order = request.GET.get('order', 'desc')
    
    books = Book.objects.filter(authors=author).select_related("publisher").prefetch_related("authors", "genres")
    
    # Применяем сортировку
    if sort_by == 'year':
        if order == 'desc':
            books = books.order_by('-publication_year', 'title')
        else:
            books = books.order_by('publication_year', 'title')
    else:  # sort_by == 'rating' (по умолчанию)
        if order == 'desc':
            books = books.order_by('-rating', 'title')
        else:
            books = books.order_by('rating', 'title')
    
    context = {
        'books': books,
        'author': author,
        'sort_by': sort_by,
        'order': order,
        'filter_type': 'author',
    }
    return render(request, "books_filtered.html", context)


def books_by_publisher(request, publisher_id):
    """Страница книг по издателю"""
    publisher = get_object_or_404(Publisher, pk=publisher_id)
    
    # Параметры сортировки
    sort_by = request.GET.get('sort', 'rating')
    order = request.GET.get('order', 'desc')
    
    books = Book.objects.filter(publisher=publisher).select_related("publisher").prefetch_related("authors", "genres")
    
    # Применяем сортировку
    if sort_by == 'year':
        if order == 'desc':
            books = books.order_by('-publication_year', 'title')
        else:
            books = books.order_by('publication_year', 'title')
    else:  # sort_by == 'rating' (по умолчанию)
        if order == 'desc':
            books = books.order_by('-rating', 'title')
        else:
            books = books.order_by('rating', 'title')
    
    context = {
        'books': books,
        'publisher': publisher,
        'sort_by': sort_by,
        'order': order,
        'filter_type': 'publisher',
    }
    return render(request, "books_filtered.html", context)


def search_books(request):
    """Глобальный поиск книг по названию, автору, жанру и издателю"""
    query = request.GET.get('q', '').strip()
    books = Book.objects.none()
    
    if query:
        from django.db.models import Q
        # Объединяем все условия поиска в один Q объект
        books = Book.objects.filter(
            Q(title__icontains=query) |
            Q(authors__first_name__icontains=query) |
            Q(authors__last_name__icontains=query) |
            Q(authors__middle_name__icontains=query) |
            Q(genres__name__icontains=query) |
            Q(publisher__name__icontains=query)
        ).select_related("publisher").prefetch_related("authors", "genres").distinct()
    
    # Параметры сортировки
    sort_by = request.GET.get('sort', 'rating')
    order = request.GET.get('order', 'desc')
    
    # Применяем сортировку
    if sort_by == 'year':
        if order == 'desc':
            books = books.order_by('-publication_year', 'title')
        else:
            books = books.order_by('publication_year', 'title')
    else:  # sort_by == 'rating'
        if order == 'desc':
            books = books.order_by('-rating', 'title')
        else:
            books = books.order_by('rating', 'title')
    
    context = {
        'books': books,
        'query': query,
        'sort_by': sort_by,
        'order': order,
        'filter_type': 'search',
    }
    return render(request, "books_filtered.html", context)


def stationery_list(request):
    stationery_items = Stationery.objects.all()
    return render(request, "stationery_list.html", {"stationery": stationery_items})


# ---------- Helpers ----------

def _get_product_or_404(product_type: str, pk: int):
    if product_type == "book":
        queryset = Book.objects.select_related("publisher").prefetch_related("authors", "genres")
    elif product_type == "stationery":
        queryset = Stationery.objects.select_related("category")
    else:
        raise Http404("Неизвестный тип товара")
    return get_object_or_404(queryset, pk=pk)


def _get_cart(request):
    return request.session.setdefault("cart", {})


def _serialize_product_for_cart(product_type, product):
    image_url = None

    if product_type == "book" and product.cover:
        image_url = product.cover.url
    elif product_type == "stationery" and getattr(product, "image", None):
        image_field = getattr(product, "image")
        if image_field:
            image_url = image_field.url

    name = product.title if product_type == "book" else product.name

    return {
        "product_type": product_type,
        "product_id": product.id,
        "name": name,
        "price": str(product.price),
        "image": image_url,
        "quantity": 0,
    }


def _cart_items_summary(cart):
    items = []
    total = Decimal("0.00")
    total_quantity = 0

    for key, item in cart.items():
        price = Decimal(item["price"])
        quantity = item["quantity"]
        subtotal = price * quantity
        total += subtotal
        total_quantity += quantity
        items.append(
            {
                "key": key,
                "product_type": item["product_type"],
                "product_id": item["product_id"],
                "name": item["name"],
                "price": price,
                "quantity": quantity,
                "subtotal": subtotal,
                "image": item.get("image"),
            }
        )

    return items, total, total_quantity


# ---------- Product Detail & Cart ----------

def product_detail(request, product_type: str, pk: int):
    product = _get_product_or_404(product_type, pk)

    # Для книг загружаем все отзывы
    reviews = None
    if product_type == "book":
        reviews = product.reviews.select_related("user").order_by("-created_at").all()

    # Логируем просмотр товара
    model_name = 'Book' if product_type == 'book' else 'Stationery'
    product_name = product.title if product_type == 'book' else product.name
    log_action(
        action='view',
        user=request.user if request.user.is_authenticated else None,
        request=request,
        model_name=model_name,
        object_id=product.id,
        object_repr=product_name,
        description=f'Просмотр {"книги" if product_type == "book" else "товара"}: {product_name}',
    )

    context = {
        "product_type": product_type,
        "product": product,
        "reviews": reviews,
    }
    return render(request, "product_detail.html", context)


@require_POST
def add_to_cart(request, product_type: str, pk: int):
    product = _get_product_or_404(product_type, pk)

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 1
    quantity = max(1, quantity)

    cart = _get_cart(request)
    key = f"{product_type}:{pk}"

    if key not in cart:
        cart[key] = _serialize_product_for_cart(product_type, product)

    cart[key]["quantity"] += quantity
    request.session.modified = True

    product_name = product.title if product_type == "book" else product.name
    messages.success(request, f'Товар "{product_name}" добавлен в корзину!')

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or reverse("cart_view")
    return redirect(next_url)


def cart_view(request):
    cart = request.session.get("cart", {})
    items, total, total_quantity = _cart_items_summary(cart)

    context = {
        "items": items,
        "total": total,
        "total_quantity": total_quantity,
    }
    return render(request, "cart.html", context)


@require_POST
def remove_from_cart(request, product_type: str, pk: int):
    key = f"{product_type}:{pk}"
    cart = request.session.get("cart", {})

    if key in cart:
        del cart[key]
        request.session.modified = True

    return redirect("cart_view")


@require_POST
def update_cart_quantity(request, product_type: str, pk: int):
    key = f"{product_type}:{pk}"
    cart = request.session.get("cart", {})

    if key not in cart:
        return redirect("cart_view")

    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = cart[key]["quantity"]

    if quantity <= 0:
        del cart[key]
    else:
        cart[key]["quantity"] = quantity

    request.session.modified = True
    return redirect("cart_view")


def checkout(request):
    from .models import DeliveryOption
    
    cart = request.session.get("cart", {})
    if not cart:
        messages.warning(request, "Корзина пуста. Добавьте товары перед оформлением заказа.")
        return redirect("cart_view")

    items, total, total_quantity = _cart_items_summary(cart)

    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user if request.user.is_authenticated else None)
        if form.is_valid():
            # Добавляем стоимость доставки к итоговой сумме
            order_total_before_bonuses = total
            delivery_option = form.cleaned_data.get("delivery_option")
            if delivery_option:
                order_total_before_bonuses += delivery_option.price

            # Используемые бонусы (если пользователь выбрал использовать бонусы)
            used_bonuses = Decimal('0')
            order_total_after_bonuses = order_total_before_bonuses
            
            if request.user.is_authenticated:
                used_bonuses_str = request.POST.get('use_bonuses', '0')
                try:
                    used_bonuses = Decimal(str(used_bonuses_str))
                except (ValueError, TypeError):
                    used_bonuses = Decimal('0')
                
                # Применяем бонусы к итоговой сумме (если пользователь авторизован)
                if used_bonuses > 0:
                    try:
                        loyalty_card = LoyaltyCard.objects.get(user=request.user)
                        if loyalty_card.balance >= used_bonuses:
                            # Не позволяем использовать бонусов больше, чем сумма заказа
                            max_bonuses = min(used_bonuses, order_total_before_bonuses)
                            # Списываем бонусы
                            loyalty_card.spend_bonus(max_bonuses)
                            # Уменьшаем итоговую сумму
                            order_total_after_bonuses = max(Decimal('0'), order_total_before_bonuses - max_bonuses)
                            used_bonuses = max_bonuses
                            if used_bonuses < Decimal(str(used_bonuses_str)):
                                messages.info(request, f"Использовано {used_bonuses} бонусов (максимум для этого заказа)")
                        else:
                            used_bonuses = Decimal('0')
                            messages.warning(request, "Недостаточно бонусов на карте лояльности")
                    except LoyaltyCard.DoesNotExist:
                        used_bonuses = Decimal('0')

            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=form.cleaned_data["full_name"],
                email=form.cleaned_data["email"],
                phone=form.cleaned_data["phone"],
                fulfillment_type=form.cleaned_data["fulfillment_type"],
                delivery_option=delivery_option,
                delivery_address=form.cleaned_data.get("delivery_address", ""),
                pickup_point=form.cleaned_data.get("pickup_point"),
                comment=form.cleaned_data.get("comment", ""),
                total_amount=order_total_after_bonuses,
            )

            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product_type=item["product_type"],
                    product_id=item["product_id"],
                    name=item["name"],
                    unit_price=item["price"],
                    quantity=item["quantity"],
                    subtotal=item["subtotal"],
                )

            # Если выбрана новая карта и пользователь авторизован, сохраняем карту
            if request.user.is_authenticated and not form.cleaned_data.get("payment_card"):
                new_card_number = form.cleaned_data.get("new_card_number", "").replace(" ", "")
                if new_card_number:
                    PaymentCard.objects.create(
                        user=request.user,
                        card_number_last4=new_card_number[-4:],
                        cardholder_name=form.cleaned_data.get("new_cardholder_name", ""),
                        expiry_month=form.cleaned_data.get("new_card_expiry_month", 1),
                        expiry_year=form.cleaned_data.get("new_card_expiry_year", 2024),
                        is_default=False,
                    )

            # Начисляем бонусы на карту лояльности (если пользователь авторизован)
            # Начисляем на сумму ДО применения бонусов
            if request.user.is_authenticated:
                try:
                    loyalty_card = LoyaltyCard.objects.get(user=request.user)
                    # Начисляем бонусы на сумму заказа ДО применения бонусов
                    bonus = loyalty_card.add_purchase(float(order_total_before_bonuses))
                    if bonus > 0:
                        messages.info(request, f"Начислено {bonus:.2f} бонусов на вашу карту лояльности!")
                except LoyaltyCard.DoesNotExist:
                    # Создаем карту лояльности при первой покупке
                    loyalty_card = LoyaltyCard.objects.create(user=request.user)
                    bonus = loyalty_card.add_purchase(float(order_total_before_bonuses))
                    if bonus > 0:
                        messages.info(request, f"Создана карта лояльности! Начислено {bonus:.2f} бонусов!")

            request.session["cart"] = {}
            request.session.modified = True

            # Логируем создание заказа
            log_action(
                action='create',
                user=request.user if request.user.is_authenticated else None,
                request=request,
                model_name='Order',
                object_id=order.id,
                object_repr=f'Заказ #{order.id}',
                description=f'Создан заказ #{order.id} на сумму {order.total_amount} руб. ({order.get_fulfillment_type_display()})',
            )

            messages.success(request, "Заказ успешно создан!")
            return redirect("order_success", order_id=order.id)
    else:
        initial = {}
        if request.user.is_authenticated:
            initial.update(
                {
                    "full_name": f"{request.user.last_name or ''} {request.user.first_name or ''}".strip(),
                    "email": request.user.email,
                    "phone": request.user.phone or "",
                }
            )
        initial.setdefault("fulfillment_type", Order.FulfillmentType.DELIVERY)
        form = CheckoutForm(initial=initial, user=request.user if request.user.is_authenticated else None)

    # Для авторизованных пользователей загружаем сохраненные адреса и карты
    saved_addresses = None
    payment_cards = None
    if request.user.is_authenticated:
        saved_addresses = SavedAddress.objects.filter(user=request.user)
        payment_cards = PaymentCard.objects.filter(user=request.user)

    # Получаем все опции доставки для передачи в шаблон
    delivery_options = DeliveryOption.objects.filter(is_active=True)

    # Получаем карту лояльности для авторизованных пользователей
    loyalty_card = None
    if request.user.is_authenticated:
        try:
            loyalty_card = LoyaltyCard.objects.get(user=request.user)
        except LoyaltyCard.DoesNotExist:
            pass

    return render(
        request,
        "checkout.html",
        {
            "form": form,
            "items": items,
            "total": total,
            "total_quantity": total_quantity,
            "delivery_choice": Order.FulfillmentType.DELIVERY,
            "pickup_choice": Order.FulfillmentType.PICKUP,
            "saved_addresses": saved_addresses,
            "payment_cards": payment_cards,
            "delivery_options": delivery_options,
            "loyalty_card": loyalty_card,
        },
    )


def order_success(request, order_id: int):
    order = get_object_or_404(Order.objects.select_related("delivery_option", "pickup_point"), pk=order_id)
    return render(
        request,
        "order_success.html",
        {"order": order},
    )
