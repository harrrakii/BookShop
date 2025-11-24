from decimal import Decimal

from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission


# --- Роли пользователей ---
class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# --- Пользователи ---
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=100, blank=True, null=True, unique=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True, help_text="Дата рождения (можно указать только один раз)")
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    groups = models.ManyToManyField(Group, related_name='core_user_set', blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name='core_user_permissions_set', blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.username or self.email

    def get_full_name(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(filter(None, parts)) or self.username or self.email
    
    def is_birthday_today(self):
        """Проверяет, день ли рождения сегодня"""
        if not self.birth_date:
            return False
        from datetime import date
        today = date.today()
        return today.month == self.birth_date.month and today.day == self.birth_date.day
    
    @property
    def is_admin(self):
        """Проверяет, является ли пользователь админом"""
        return self.is_superuser or (self.role and self.role.name.lower() == 'админ')
    
    def is_admin_method(self):
        """Проверяет, является ли пользователь админом (метод для проверок в коде)"""
        return self.is_superuser or (self.role and self.role.name.lower() == 'админ')
    
    @property
    def is_manager(self):
        """Проверяет, является ли пользователь менеджером"""
        return (self.is_staff and not self.is_superuser) or (self.role and self.role.name.lower() == 'менеджер')
    
    def is_manager_method(self):
        """Проверяет, является ли пользователь менеджером (метод для проверок в коде)"""
        return (self.is_staff and not self.is_superuser) or (self.role and self.role.name.lower() == 'менеджер')
    
    @property
    def is_user(self):
        """Проверяет, является ли пользователь обычным пользователем"""
        return not self.is_superuser and not self.is_staff and (not self.role or self.role.name.lower() == 'пользователь')


# --- Категории ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# --- Издатели ---
class Publisher(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# --- Авторы ---
class Author(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    photo = models.ImageField(upload_to='authors/', blank=True, null=True, help_text="Фото автора")
    birth_date = models.DateField(blank=True, null=True, help_text="Дата рождения")
    birth_place = models.CharField(max_length=255, blank=True, null=True, help_text="Место рождения")
    death_date = models.DateField(blank=True, null=True, help_text="Дата смерти")
    death_place = models.CharField(max_length=255, blank=True, null=True, help_text="Место смерти")
    biography = models.TextField(blank=True, null=True, help_text="Биография автора")
    short_bio = models.TextField(blank=True, null=True, help_text="Краткая биография (для карточек)")

    class Meta:
        ordering = ('last_name', 'first_name')

    def __str__(self):
        full_name = f"{self.last_name} {self.first_name}"
        if self.middle_name:
            full_name += f" {self.middle_name}"
        return full_name
    
    def get_full_name(self):
        """Возвращает полное имя автора"""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.insert(1, self.middle_name)
        return " ".join(parts)
    
    def get_books(self):
        """Возвращает все книги автора"""
        return self.books.all()


# --- Жанры ---
class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# --- Книги ---
class Book(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    isbn13 = models.CharField(max_length=20, unique=True)
    publication_year = models.PositiveIntegerField(blank=True, null=True)
    language = models.CharField(max_length=50)
    cover = models.ImageField(upload_to='books/', blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, help_text="Рейтинг от 0.00 до 5.00")

    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True, related_name='books')
    authors = models.ManyToManyField(Author, related_name='books')
    genres = models.ManyToManyField(Genre, related_name='books')

    def __str__(self):
        return self.title

    def update_rating(self):
        """Пересчитывает средний рейтинг книги на основе отзывов"""
        from django.db.models import Avg
        avg_rating = self.reviews.aggregate(Avg('rating'))['rating__avg']
        if avg_rating is not None:
            self.rating = round(Decimal(str(avg_rating)), 2)
        else:
            self.rating = Decimal('0.00')
        self.save(update_fields=['rating'])


# --- Канцтовары ---
class Stationery(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name


# --- Продукты ---
class Product(models.Model):
    PRODUCT_TYPES = (
        ('book', 'Book'),
        ('stationery', 'Stationery'),
    )
    product_type = models.CharField(max_length=50, choices=PRODUCT_TYPES)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True)
    stationery = models.ForeignKey(Stationery, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.product_type} - {self.book or self.stationery}"


# --- Доставка ---
class DeliveryOption(models.Model):
    name = models.CharField(max_length=150)
    min_days = models.PositiveIntegerField()
    max_days = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("min_days", "max_days")

    def __str__(self):
        if self.min_days == self.max_days:
            duration = f"{self.min_days} день"
        else:
            duration = f"{self.min_days}-{self.max_days} дней"
        return f"{self.name} ({duration})"


class PickupPoint(models.Model):
    name = models.CharField(max_length=150)
    city = models.CharField(max_length=120)
    address = models.CharField(max_length=255)
    working_hours = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("city", "name")

    def __str__(self):
        return f"{self.city}, {self.address}"


class Order(models.Model):
    class FulfillmentType(models.TextChoices):
        DELIVERY = "delivery", "Доставка"
        PICKUP = "pickup", "Самовывоз"

    class Status(models.TextChoices):
        NEW = "new", "Новый"
        PROCESSING = "processing", "В обработке"
        SHIPPED = "shipped", "Отправлен"
        COMPLETED = "completed", "Завершен"
        CANCELLED = "cancelled", "Отменен"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    fulfillment_type = models.CharField(max_length=20, choices=FulfillmentType.choices)
    delivery_option = models.ForeignKey(
        DeliveryOption, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    delivery_address = models.TextField(blank=True)
    pickup_point = models.ForeignKey(
        PickupPoint, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    comment = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Заказ #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_type = models.CharField(max_length=50, choices=Product.PRODUCT_TYPES)
    product_id = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} x{self.quantity}"


# --- Отзывы ---
class Review(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="reviews",
        help_text="Отзыв можно оставить только после завершения заказа",
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="reviews",
        null=True,
        blank=True,
    )
    rating = models.PositiveIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        help_text="Оценка от 1 до 5",
    )
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "order", "book")]
        ordering = ("-created_at",)

    def __str__(self):
        return f"Отзыв от {self.user} на {self.book or 'заказ'}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.book:
            self.book.update_rating()


# --- Сохраненные адреса ---
class SavedAddress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_addresses",
    )
    title = models.CharField(max_length=100, help_text="Название адреса (например, 'Дом', 'Работа')")
    address = models.TextField()
    city = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-is_default", "-created_at")

    def __str__(self):
        return f"{self.title} - {self.city}, {self.address}"

    def save(self, *args, **kwargs):
        if self.is_default:
            SavedAddress.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


# --- Привязанные карты ---
class PaymentCard(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_cards",
    )
    card_number_last4 = models.CharField(max_length=4, help_text="Последние 4 цифры карты")
    cardholder_name = models.CharField(max_length=255)
    expiry_month = models.PositiveIntegerField()
    expiry_year = models.PositiveIntegerField()
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-is_default", "-created_at")

    def __str__(self):
        return f"**** **** **** {self.card_number_last4}"

    def save(self, *args, **kwargs):
        if self.is_default:
            PaymentCard.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


# --- Карта лояльности ---
class LoyaltyCard(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loyalty_card",
    )
    card_number = models.CharField(max_length=16, unique=True, help_text="Номер карты лояльности")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Баланс бонусов")
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Общая сумма покупок")
    created_at = models.DateTimeField(auto_now_add=True)
    last_birthday_bonus = models.DateField(blank=True, null=True, help_text="Дата последнего начисления бонусов на день рождения")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Карта лояльности {self.card_number} - {self.user.email}"

    def get_bonus_percentage(self):
        """Возвращает процент начисления бонусов в зависимости от общей суммы покупок"""
        total = float(self.total_spent)
        if total >= 250000:
            return 10
        elif total >= 150000:
            return 7
        elif total >= 100000:
            return 6
        elif total >= 60000:
            return 5
        elif total >= 30000:
            return 4
        elif total >= 15000:
            return 3
        else:
            return 1

    def calculate_bonus(self, amount):
        """Рассчитывает количество бонусов для указанной суммы"""
        percentage = self.get_bonus_percentage()
        return Decimal(str(amount)) * Decimal(str(percentage)) / Decimal('100')

    def add_bonus(self, amount):
        """Добавляет бонусы на карту"""
        self.balance += Decimal(str(amount))
        self.save(update_fields=['balance', 'updated_at'])

    def spend_bonus(self, amount):
        """Списывает бонусы с карты"""
        amount_decimal = Decimal(str(amount))
        if self.balance >= amount_decimal:
            self.balance -= amount_decimal
            self.save(update_fields=['balance', 'updated_at'])
            return True
        return False

    def add_purchase(self, amount):
        """Добавляет покупку и начисляет бонусы"""
        bonus = self.calculate_bonus(amount)
        amount_decimal = Decimal(str(amount))
        self.total_spent += amount_decimal
        # Обновляем баланс и total_spent в одной транзакции
        self.balance += bonus
        self.save(update_fields=['balance', 'total_spent', 'updated_at'])
        return bonus

    @staticmethod
    def generate_card_number():
        """Генерирует уникальный номер карты лояльности"""
        import random
        import string
        while True:
            # Генерируем 16-значный номер карты
            card_number = ''.join(random.choices(string.digits, k=16))
            if not LoyaltyCard.objects.filter(card_number=card_number).exists():
                return card_number

    def save(self, *args, **kwargs):
        if not self.card_number:
            self.card_number = self.generate_card_number()
        super().save(*args, **kwargs)


# --- Избранное (Wishlist) ---
class Wishlist(models.Model):
    """Избранные товары пользователя"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    book = models.ForeignKey('Book', on_delete=models.CASCADE, null=True, blank=True)
    stationery = models.ForeignKey('Stationery', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ('user', 'book'),
            ('user', 'stationery'),
        ]
        ordering = ('-created_at',)
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        product = self.book or self.stationery
        product_name = product.title if self.book else product.name
        return f"{self.user.email} - {product_name}"

    @property
    def product(self):
        """Возвращает продукт (книгу или канцтовар)"""
        return self.book or self.stationery

    @property
    def product_type(self):
        """Возвращает тип продукта"""
        return 'book' if self.book else 'stationery'


# --- FAQ (Часто задаваемые вопросы) ---
class FAQ(models.Model):
    """Часто задаваемые вопросы для чата поддержки"""
    question = models.CharField(max_length=500, help_text="Вопрос пользователя")
    answer = models.TextField(help_text="Ответ на вопрос")
    category = models.CharField(
        max_length=50,
        choices=[
            ('delivery', 'Доставка'),
            ('return', 'Возврат'),
            ('payment', 'Оплата'),
            ('order', 'Заказ'),
            ('loyalty', 'Программа лояльности'),
            ('other', 'Другое'),
        ],
        default='other'
    )
    order = models.PositiveIntegerField(default=0, help_text="Порядок отображения")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('order', 'question')
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQ'

    def __str__(self):
        return self.question[:50]


# --- Сообщения поддержки ---
class SupportMessage(models.Model):
    """Сообщения пользователей в чат поддержки (когда нет ответа в FAQ)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_messages",
        help_text="Пользователь (если авторизован)"
    )
    name = models.CharField(max_length=255, help_text="Имя пользователя")
    email = models.EmailField(help_text="Email для ответа")
    message = models.TextField(help_text="Текст сообщения")
    attachment = models.FileField(
        upload_to='support_messages/',
        blank=True,
        null=True,
        help_text="Прикрепленный файл (фото, документ и т.д.)"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'Новое'),
            ('in_progress', 'В обработке'),
            ('resolved', 'Решено'),
            ('closed', 'Закрыто'),
        ],
        default='new'
    )
    admin_response = models.TextField(blank=True, null=True, help_text="Ответ администратора")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Сообщение поддержки'
        verbose_name_plural = 'Сообщения поддержки'

    def __str__(self):
        return f"Сообщение от {self.name} ({self.email})"


# --- Журнал аудита ---
class AuditLog(models.Model):
    """Журнал аудита для отслеживания всех действий пользователей"""
    ACTION_TYPES = (
        # Действия с контентом
        ('create', 'Создание'),
        ('update', 'Изменение'),
        ('delete', 'Удаление'),
        ('view', 'Просмотр'),
        ('download', 'Скачивание'),
        # Действия пользователей
        ('login', 'Вход в систему'),
        ('logout', 'Выход из системы'),
        ('register', 'Регистрация'),
        ('password_reset', 'Сброс пароля'),
        # Действия администратора
        ('config', 'Изменение конфигурации'),
        ('export', 'Экспорт данных'),
        ('import', 'Импорт данных'),
        # Прочие
        ('other', 'Прочее'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Пользователь, который выполнил действие (null для неавторизованных)"
    )
    action = models.CharField(max_length=20, choices=ACTION_TYPES, default='other', help_text="Тип действия")
    model_name = models.CharField(max_length=100, blank=True, null=True, help_text="Название модели (если применимо)")
    object_id = models.PositiveIntegerField(null=True, blank=True, help_text="ID объекта (если применимо)")
    object_repr = models.CharField(max_length=255, blank=True, null=True, help_text="Строковое представление объекта")
    
    # Дополнительная информация о действии
    description = models.TextField(blank=True, null=True, help_text="Описание действия")
    url_path = models.CharField(max_length=500, blank=True, null=True, help_text="URL страницы")
    
    # Изменения в формате JSON (для create/update/delete)
    changes = models.JSONField(default=dict, blank=True, help_text="Изменения (поле: {old: значение, new: значение})")
    
    # Дополнительная информация
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="IP адрес")
    user_agent = models.TextField(blank=True, null=True, help_text="User Agent")
    
    created_at = models.DateTimeField(auto_now_add=True, help_text="Время действия")
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Запись аудита'
        verbose_name_plural = 'Журнал аудита'
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} {self.model_name} #{self.object_id} by {self.user or 'System'}"
    
    def get_changes_display(self):
        """Возвращает форматированное отображение изменений"""
        if not self.changes:
            return "Нет изменений"
        
        result = []
        for field, values in self.changes.items():
            old_val = values.get('old', '—')
            new_val = values.get('new', '—')
            result.append(f"{field}: {old_val} → {new_val}")
        
        return "; ".join(result)
