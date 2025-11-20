from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Author,
    Book,
    Category,
    DeliveryOption,
    Genre,
    LoyaltyCard,
    Order,
    OrderItem,
    PaymentCard,
    PickupPoint,
    Product,
    Publisher,
    Review,
    Role,
    SavedAddress,
    Stationery,
    User,
)
from .forms import CustomUserCreationForm, CustomUserChangeForm


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "isbn13", "price", "rating", "publisher", "stock_quantity")
    list_filter = ("publisher", "language")
    search_fields = ("title", "isbn13")
    readonly_fields = ("rating",)


@admin.register(Stationery)
class StationeryAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock_quantity")
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_type", "book", "stationery")
    list_filter = ("product_type",)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "middle_name")
    search_fields = ("last_name", "first_name")


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админ-панель для пользователей с правильной обработкой паролей"""
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = ("email", "username", "first_name", "last_name", "role", "is_staff", "is_superuser", "is_active")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)
    
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "middle_name", "phone", "avatar", "birth_date")}),
        ("Role", {"fields": ("role",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login",)}),
    )
    
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2", "role"),
        }),
    )
    
    readonly_fields = ("last_login",)
    
    def save_model(self, request, obj, form, change):
        """Сохраняет модель с правильным хешированием пароля и установкой ролей"""
        # Автоматически устанавливаем is_staff и is_superuser в зависимости от роли
        if obj.role:
            role_name_lower = obj.role.name.lower()
            if role_name_lower == 'менеджер':
                obj.is_staff = True
                # Менеджер не должен быть суперпользователем
                obj.is_superuser = False
            elif role_name_lower == 'пользователь':
                obj.is_staff = False
                obj.is_superuser = False
            elif role_name_lower == 'админ':
                obj.is_staff = True
                obj.is_superuser = True
        
        # Сохраняем модель (пароль уже обработан формой UserCreationForm/UserChangeForm)
        super().save_model(request, obj, form, change)


@admin.register(LoyaltyCard)
class LoyaltyCardAdmin(admin.ModelAdmin):
    list_display = ("card_number", "user", "balance", "total_spent", "get_bonus_percentage_display", "created_at")
    list_filter = ("created_at",)
    search_fields = ("card_number", "user__email", "user__username")
    readonly_fields = ("card_number", "created_at", "updated_at")
    
    def get_bonus_percentage_display(self, obj):
        return f"{obj.get_bonus_percentage()}%"
    get_bonus_percentage_display.short_description = "Процент бонусов"


@admin.register(DeliveryOption)
class DeliveryOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "min_days", "max_days", "price", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(PickupPoint)
class PickupPointAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "address", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("name", "city", "address")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_type", "name", "quantity", "unit_price", "subtotal")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "fulfillment_type", "total_amount", "status", "created_at")
    list_filter = ("status", "fulfillment_type", "created_at")
    search_fields = ("full_name", "email", "phone")
    inlines = (OrderItemInline,)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "order", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("user__email", "book__title", "comment")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SavedAddress)
class SavedAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "city", "address", "is_default", "created_at")
    list_filter = ("city", "is_default", "created_at")
    search_fields = ("user__email", "title", "city", "address")


@admin.register(PaymentCard)
class PaymentCardAdmin(admin.ModelAdmin):
    list_display = ("user", "card_number_last4", "cardholder_name", "expiry_month", "expiry_year", "is_default", "created_at")
    list_filter = ("is_default", "created_at")
    search_fields = ("user__email", "cardholder_name", "card_number_last4")
    readonly_fields = ("created_at",)
