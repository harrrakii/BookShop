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
)

router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("publishers", PublisherViewSet)
router.register("books", BookViewSet)
router.register("stationery", StationeryViewSet)
router.register("products", ProductViewSet)
router.register("authors", AuthorViewSet)
router.register("genres", GenreViewSet)

urlpatterns = router.urls
