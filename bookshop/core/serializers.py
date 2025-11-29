from rest_framework import serializers
from .models import (
    Category,
    Publisher,
    Book,
    Stationery,
    Product,
    Author,
    Genre,
    Role,
    User,
    DeliveryOption,
    PickupPoint,
    Order,
    OrderItem,
    Review,
    SavedAddress,
    PaymentCard,
    LoyaltyCard,
    Wishlist,
    FAQ,
    SupportMessage,
    AuditLog,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = "__all__"


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = "__all__"


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = "__all__"


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = "__all__"


class StationerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Stationery
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'middle_name',
            'phone', 'avatar', 'birth_date', 'role', 'role_name', 'is_active',
            'is_staff', 'is_superuser', 'last_login'
        ]
        read_only_fields = ['id', 'last_login', 'is_superuser']


class DeliveryOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryOption
        fields = "__all__"


class PickupPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupPoint
        fields = "__all__"


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Order
        fields = "__all__"


class ReviewSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    
    class Meta:
        model = Review
        fields = "__all__"


class SavedAddressSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = SavedAddress
        fields = "__all__"


class PaymentCardSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = PaymentCard
        fields = "__all__"


class LoyaltyCardSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = LoyaltyCard
        fields = "__all__"


class WishlistSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True, allow_null=True)
    stationery_name = serializers.CharField(source='stationery.name', read_only=True, allow_null=True)
    
    class Meta:
        model = Wishlist
        fields = "__all__"


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = "__all__"


class SupportMessageSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    
    class Meta:
        model = SupportMessage
        fields = "__all__"


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True, allow_null=True)
    
    class Meta:
        model = AuditLog
        fields = "__all__"
