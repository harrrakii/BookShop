from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager, Group, Permission

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


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
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # 🧩 добавляем эти две строки, чтобы не конфликтовать с auth.User
    groups = models.ManyToManyField(
        Group,
        related_name='core_user_set',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='core_user_permissions_set',
        blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

# --- Категории ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# --- Издатели ---
class Publisher(models.Model):
    name = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.name


# --- Книги ---
class Book(models.Model):
    isbn13 = models.CharField(max_length=20, unique=True)
    language = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Book {self.isbn13}"


# --- Канцтовары ---
class Stationery(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name


# --- Продукты (объединяет книги и канцтовары) ---
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


# --- Авторы ---
class Author(models.Model):
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


# --- Жанры ---
class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# --- Авторы-Книги (M2M) ---
class BookAuthor(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)


# --- Жанры-Книги (M2M) ---
class BookGenre(models.Model):
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
