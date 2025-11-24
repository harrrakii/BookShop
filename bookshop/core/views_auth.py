from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from .models import Order, Review, SavedAddress, PaymentCard, Book, OrderItem, LoyaltyCard, Role
from .forms import UserProfileForm, ReviewForm, SavedAddressForm, PaymentCardForm
from .audit import log_action
from decimal import Decimal
from datetime import date

User = get_user_model()


def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm')

        if password != confirm:
            messages.error(request, 'Пароли не совпадают')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Такой пользователь уже есть')
            return redirect('register')

        # Создаем пользователя с ролью "пользователь" по умолчанию
        user = User.objects.create_user(email=email, password=password)
        
        # Присваиваем роль "пользователь" по умолчанию
        try:
            user_role = Role.objects.get(name='пользователь')
            user.role = user_role
            user.save()
        except Role.DoesNotExist:
            # Если роли нет, создаем её
            user_role = Role.objects.create(name='пользователь')
            user.role = user_role
            user.save()
        
        # Логируем регистрацию
        log_action(
            action='register',
            user=user,
            request=request,
            description=f'Регистрация нового пользователя: {email}',
        )
        
        messages.success(request, 'Регистрация успешна! Войдите в аккаунт.')
        return redirect('login')

    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)
        if user:
            login(request, user)
            # Логируем вход в систему
            log_action(
                action='login',
                user=user,
                request=request,
                description=f'Вход в систему: {email}',
            )
            return redirect('home')
        else:
            messages.error(request, 'Неверный логин или пароль')
            # Логируем неудачную попытку входа
            log_action(
                action='login',
                user=None,
                request=request,
                description=f'Неудачная попытка входа: {email}',
            )

    return render(request, 'login.html')


@login_required
def profile_view(request):
    user = request.user
    orders = Order.objects.filter(user=user).select_related("delivery_option", "pickup_point").prefetch_related("items")[:20]
    reviews = Review.objects.filter(user=user).select_related("book", "order")[:20]
    saved_addresses = SavedAddress.objects.filter(user=user)
    payment_cards = PaymentCard.objects.filter(user=user)

    # Получаем карту лояльности
    loyalty_card = None
    try:
        loyalty_card = LoyaltyCard.objects.get(user=user)
    except LoyaltyCard.DoesNotExist:
        pass

    # Если карта существует, но total_spent равен 0 или очень мал, пересчитываем на основе существующих заказов
    if loyalty_card:
        # Проверяем, нужно ли пересчитать total_spent
        zero_decimal = Decimal('0')
        if loyalty_card.total_spent == zero_decimal or loyalty_card.total_spent is None:
            # Суммируем все заказы пользователя
            user_orders = Order.objects.filter(user=user)
            total_spent_from_orders = sum([Decimal(str(order.total_amount)) for order in user_orders])
            if total_spent_from_orders > zero_decimal:
                # Обновляем total_spent на основе существующих заказов
                loyalty_card.total_spent = total_spent_from_orders
                # Сохраняем текущий баланс для сравнения
                current_balance = loyalty_card.balance
                # Пересчитываем процент бонусов на основе новой суммы
                bonus_percentage = loyalty_card.get_bonus_percentage()
                # Пересчитываем баланс бонусов на основе total_spent
                # Вычисляем, сколько бонусов должно быть на основе total_spent
                expected_bonus = loyalty_card.total_spent * Decimal(str(bonus_percentage)) / Decimal('100')
                # Если текущий баланс меньше ожидаемого, обновляем его
                # Но не уменьшаем баланс, если он больше (возможно, были бонусы на день рождения)
                if current_balance < expected_bonus:
                    loyalty_card.balance = expected_bonus
                # Сохраняем изменения
                loyalty_card.save(update_fields=['total_spent', 'balance', 'updated_at'])
                # Обновляем объект loyalty_card для контекста
                loyalty_card.refresh_from_db()

    # Проверяем день рождения и начисляем бонусы
    if user.birth_date:
        today = date.today()
        if user.birth_date.month == today.month and user.birth_date.day == today.day:
            if loyalty_card:
                # Проверяем, не начисляли ли бонусы в этом году
                if not loyalty_card.last_birthday_bonus or loyalty_card.last_birthday_bonus.year < today.year:
                    # Начисляем 1000 бонусов на день рождения
                    loyalty_card.add_bonus(Decimal('1000'))
                    loyalty_card.last_birthday_bonus = today
                    loyalty_card.save(update_fields=['balance', 'last_birthday_bonus', 'updated_at'])
                    messages.success(request, "🎉 С Днем Рождения! Вам начислено 1000 бонусов!")
                    # Обновляем объект loyalty_card для контекста
                    loyalty_card.refresh_from_db()
            else:
                # Создаем карту лояльности, если её нет
                loyalty_card = LoyaltyCard.objects.create(user=user)
                loyalty_card.add_bonus(Decimal('1000'))
                loyalty_card.last_birthday_bonus = today
                loyalty_card.save(update_fields=['balance', 'last_birthday_bonus', 'updated_at'])
                messages.success(request, "🎉 С Днем Рождения! Создана карта лояльности и начислено 1000 бонусов!")

    # Заказы, для которых можно оставить отзыв
    completed_orders = Order.objects.filter(user=user, status=Order.Status.COMPLETED).prefetch_related("items", "reviews")
    reviewable_orders = []
    for order in completed_orders:
        for item in order.items.all():
            if item.product_type == "book":
                book = Book.objects.filter(pk=item.product_id).first()
                if book:
                    existing_review = Review.objects.filter(user=user, order=order, book=book).first()
                    if not existing_review:
                        reviewable_orders.append({
                            "order": order,
                            "book": book,
                            "item": item,
                        })

    context = {
        "user": user,
        "orders": orders,
        "reviews": reviews,
        "saved_addresses": saved_addresses,
        "payment_cards": payment_cards,
        "reviewable_orders": reviewable_orders,
        "loyalty_card": loyalty_card,
    }
    return render(request, 'profile.html', context)


@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'edit_profile.html', {'form': form})


@login_required
def add_review(request, order_id, book_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user, status=Order.Status.COMPLETED)
    book = get_object_or_404(Book, pk=book_id)
    
    # Проверяем, что книга была в этом заказе
    order_item = OrderItem.objects.filter(order=order, product_type="book", product_id=book.id).first()
    if not order_item:
        messages.error(request, 'Эта книга не была в данном заказе')
        return redirect('profile')
    
    # Проверяем, что отзыв еще не оставлен
    existing_review = Review.objects.filter(user=request.user, order=order, book=book).first()
    if existing_review:
        messages.error(request, 'Вы уже оставили отзыв на эту книгу из этого заказа')
        return redirect('profile')
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.order = order
            review.book = book
            review.save()
            messages.success(request, 'Отзыв успешно добавлен!')
            return redirect('profile')
    else:
        form = ReviewForm()
    
    return render(request, 'add_review.html', {'form': form, 'book': book, 'order': order})


@login_required
def add_saved_address(request):
    if request.method == 'POST':
        form = SavedAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, 'Адрес успешно добавлен!')
            return redirect('profile')
    else:
        form = SavedAddressForm()

    return render(request, 'add_saved_address.html', {'form': form})


@login_required
@require_POST
def delete_saved_address(request, address_id):
    address = get_object_or_404(SavedAddress, pk=address_id, user=request.user)
    address.delete()
    messages.success(request, 'Адрес успешно удален!')
    return redirect('profile')


@login_required
def add_payment_card(request):
    if request.method == 'POST':
        form = PaymentCardForm(request.POST)
        if form.is_valid():
            card = form.save(commit=False)
            card.user = request.user
            card.save()
            messages.success(request, 'Карта успешно добавлена!')
            return redirect('profile')
    else:
        form = PaymentCardForm()

    return render(request, 'add_payment_card.html', {'form': form})


@login_required
@require_POST
def delete_payment_card(request, card_id):
    card = get_object_or_404(PaymentCard, pk=card_id, user=request.user)
    card.delete()
    messages.success(request, 'Карта успешно удалена!')
    return redirect('profile')


@login_required
@require_POST
def delete_review(request, review_id):
    """Удаление отзыва пользователя"""
    review = get_object_or_404(Review, pk=review_id, user=request.user)
    book_title = review.book.title
    review.delete()
    
    # Логируем удаление
    log_action(
        action='delete',
        user=request.user,
        request=request,
        model_name='Review',
        object_id=review_id,
        object_repr=f'Отзыв на "{book_title}"',
        description=f'Удален отзыв на книгу "{book_title}"',
    )
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Отзыв успешно удален'})
    
    messages.success(request, 'Отзыв успешно удален!')
    return redirect('profile')


def logout_view(request):
    # Логируем выход из системы перед logout
    if request.user.is_authenticated:
        log_action(
            action='logout',
            user=request.user,
            request=request,
            description=f'Выход из системы: {request.user.email}',
        )
    logout(request)
    return redirect('login')
