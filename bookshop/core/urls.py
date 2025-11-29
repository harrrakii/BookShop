from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    PublisherViewSet,
    BookViewSet,
    StationeryViewSet,
    ProductViewSet,
    AuthorViewSet,
    GenreViewSet,
    RoleViewSet,
    UserViewSet,
    DeliveryOptionViewSet,
    PickupPointViewSet,
    OrderViewSet,
    OrderItemViewSet,
    ReviewViewSet,
    SavedAddressViewSet,
    PaymentCardViewSet,
    LoyaltyCardViewSet,
    WishlistViewSet,
    FAQViewSet,
    SupportMessageViewSet,
    AuditLogViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("publishers", PublisherViewSet)
router.register("books", BookViewSet)
router.register("stationery", StationeryViewSet)
router.register("products", ProductViewSet)
router.register("authors", AuthorViewSet)
router.register("genres", GenreViewSet)
router.register("roles", RoleViewSet)
router.register("users", UserViewSet)
router.register("delivery-options", DeliveryOptionViewSet)
router.register("pickup-points", PickupPointViewSet)
router.register("orders", OrderViewSet)
router.register("order-items", OrderItemViewSet)
router.register("reviews", ReviewViewSet)
router.register("saved-addresses", SavedAddressViewSet)
router.register("payment-cards", PaymentCardViewSet)
router.register("loyalty-cards", LoyaltyCardViewSet)
router.register("wishlist", WishlistViewSet)
router.register("faq", FAQViewSet)
router.register("support-messages", SupportMessageViewSet)
router.register("audit-logs", AuditLogViewSet)

urlpatterns = router.urls
