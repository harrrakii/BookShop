from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    Author,
    AuditLog,
    Book,
    Category,
    DeliveryOption,
    FAQ,
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
    SupportMessage,
    User,
    Wishlist,
)
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .audit import log_change


class AuditedModelAdmin(admin.ModelAdmin):
    """Базовый класс для админ-классов с аудитом"""
    def save_model(self, request, obj, form, change):
        if change:
            # Получаем старые значения
            old_instance = self.model.objects.get(pk=obj.pk)
            changes = {}
            for field in obj._meta.fields:
                if field.name in ['id', 'created_at', 'updated_at']:
                    continue
                old_value = getattr(old_instance, field.name, None)
                new_value = getattr(obj, field.name, None)
                if old_value != new_value:
                    changes[field.name] = {
                        'old': str(old_value) if old_value is not None else '—',
                        'new': str(new_value) if new_value is not None else '—'
                    }
            super().save_model(request, obj, form, change)
            if changes:
                log_change(obj, 'update', request=request, changes=changes)
        else:
            super().save_model(request, obj, form, change)
            log_change(obj, 'create', request=request)
    
    def delete_model(self, request, obj):
        log_change(obj, 'delete', request=request)
        super().delete_model(request, obj)


@admin.register(Publisher)
class PublisherAdmin(AuditedModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Book)
class BookAdmin(AuditedModelAdmin):
    list_display = ("title", "isbn13", "price", "rating", "publisher", "stock_quantity")
    list_filter = ("publisher", "language")
    search_fields = ("title", "isbn13")
    readonly_fields = ("rating",)


@admin.register(Stationery)
class StationeryAdmin(AuditedModelAdmin):
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
class AuthorAdmin(AuditedModelAdmin):
    list_display = ("last_name", "first_name", "middle_name", "birth_date", "death_date")
    search_fields = ("last_name", "first_name", "middle_name")
    list_filter = ("birth_date", "death_date")
    fieldsets = (
        (None, {"fields": ("first_name", "last_name", "middle_name", "photo")}),
        ("Биография", {"fields": ("short_bio", "biography")}),
        ("Даты", {"fields": (("birth_date", "birth_place"), ("death_date", "death_place"))}),
    )


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
class OrderAdmin(AuditedModelAdmin):
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


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "order", "is_active", "created_at")
    list_filter = ("category", "is_active", "created_at")
    search_fields = ("question", "answer")
    ordering = ("order", "question")


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "status", "has_attachment", "created_at", "user")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "message")
    readonly_fields = ("created_at", "updated_at", "attachment_preview")
    fieldsets = (
        (None, {"fields": ("user", "name", "email", "message", "attachment", "attachment_preview", "status")}),
        ("Ответ", {"fields": ("admin_response",)}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )
    
    def has_attachment(self, obj):
        return bool(obj.attachment)
    has_attachment.boolean = True
    has_attachment.short_description = "Есть файл"
    
    def attachment_preview(self, obj):
        if obj.attachment:
            if obj.attachment.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                return format_html('<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 8px;">', obj.attachment.url)
            else:
                return format_html('<a href="{}" target="_blank">📎 {}</a>', obj.attachment.url, obj.attachment.name)
        return "Нет файла"
    attachment_preview.short_description = "Превью файла"


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "get_product_name", "get_product_type", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "user__username", "book__title", "stationery__name")
    readonly_fields = ("created_at",)
    
    def get_product_name(self, obj):
        return obj.product.title if obj.book else obj.product.name
    get_product_name.short_description = "Товар"
    
    def get_product_type(self, obj):
        return "Книга" if obj.book else "Канцтовар"
    get_product_type.short_description = "Тип"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "model_name", "object_repr", "user", "description", "ip_address")
    list_filter = ("action", "model_name", "created_at")
    search_fields = ("object_repr", "model_name", "user__email", "user__username", "description", "url_path")
    readonly_fields = ("action", "model_name", "object_id", "object_repr", "description", "url_path", "get_changes_display", "user", "ip_address", "user_agent", "created_at")
    ordering = ("-created_at",)
    
    fieldsets = (
        (None, {"fields": ("action", "model_name", "object_id", "object_repr", "user", "created_at")}),
        ("Описание", {"fields": ("description", "url_path")}),
        ("Изменения", {"fields": ("get_changes_display",)}),
        ("Техническая информация", {"fields": ("ip_address", "user_agent")}),
    )
    
    def get_changes_display(self, obj):
        """Отображает изменения в читаемом виде"""
        if not obj.changes:
            return "Нет изменений"
        
        html = "<div style='max-height: 400px; overflow-y: auto;'>"
        for field, values in obj.changes.items():
            old_val = values.get('old', '—')
            new_val = values.get('new', '—')
            html += f"<div style='margin-bottom: 0.5rem; padding: 0.5rem; background: #f8f9fa; border-radius: 4px;'>"
            html += f"<strong>{field}:</strong><br>"
            html += f"<span style='color: #dc3545;'>Было: {old_val}</span><br>"
            html += f"<span style='color: #28a745;'>Стало: {new_val}</span>"
            html += "</div>"
        html += "</div>"
        return format_html(html)
    get_changes_display.short_description = "Изменения"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


