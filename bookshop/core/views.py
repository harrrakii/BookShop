from rest_framework import viewsets
from .models import (
    Category, Publisher, Book, Stationery,
    Product, Author, Genre, BookAuthor, BookGenre
)
from .serializers import (
    CategorySerializer, PublisherSerializer, BookSerializer, StationerySerializer,
    ProductSerializer, AuthorSerializer, GenreSerializer,
    BookAuthorSerializer, BookGenreSerializer
)

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

class BookAuthorViewSet(viewsets.ModelViewSet):
    queryset = BookAuthor.objects.all()
    serializer_class = BookAuthorSerializer

class BookGenreViewSet(viewsets.ModelViewSet):
    queryset = BookGenre.objects.all()
    serializer_class = BookGenreSerializer
