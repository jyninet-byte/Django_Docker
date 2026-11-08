from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from authentication.models import CustomUser
from author.models import Author
from book.models import Book
from order.models import Order

from .permissions import IsLibrarianOrReadOnly, OrderPermission, UserPermission, is_librarian
from .serializers import (AuthorSerializer, BookSerializer, OrderSerializer, UserOrderSerializer,
                          UserSerializer)


class UserViewSet(viewsets.ModelViewSet):
    """/api/v1/user/  and  /api/v1/user/{id}/  - CRUD for users."""
    serializer_class = UserSerializer
    permission_classes = (UserPermission,)

    def get_queryset(self):
        users = CustomUser.objects.prefetch_related('order_set').order_by('id')
        if is_librarian(self.request.user):
            return users
        return users.filter(pk=self.request.user.pk)

    def destroy(self, request, *args, **kwargs):
        if self.get_object() == request.user:
            raise ValidationError({'detail': 'You cannot delete yourself.'})
        return super().destroy(request, *args, **kwargs)


class OrderViewSet(viewsets.ModelViewSet):
    """/api/v1/order/  and  /api/v1/order/{id}/  - CRUD for orders."""
    serializer_class = OrderSerializer
    permission_classes = (OrderPermission,)

    def get_queryset(self):
        orders = Order.objects.select_related('user', 'book').order_by('id')
        if is_librarian(self.request.user):
            return orders
        return orders.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = serializer.validated_data.get('user')
        if not is_librarian(self.request.user) or user is None:
            user = self.request.user  # a reader always orders for himself
        serializer.save(user=user)


class UserOrderViewSet(viewsets.ModelViewSet):
    """/api/v1/user/{user_id}/order/  and  /api/v1/user/{user_id}/order/{id}/  - orders of one user."""
    serializer_class = UserOrderSerializer
    permission_classes = (OrderPermission,)

    def get_user(self):
        user = get_object_or_404(CustomUser, pk=self.kwargs['user_pk'])
        if not is_librarian(self.request.user) and user != self.request.user:
            self.permission_denied(self.request, message='You can see only your own orders.')
        return user

    def get_queryset(self):
        return Order.objects.filter(user=self.get_user()).select_related('book').order_by('id')

    def perform_create(self, serializer):
        serializer.save(user=self.get_user())


class BookViewSet(viewsets.ModelViewSet):
    """/api/v1/book/  and  /api/v1/book/{id}/  - CRUD for books.

    Filters: ?name=..., ?author=<id>, ?year=...
    """
    serializer_class = BookSerializer
    permission_classes = (IsLibrarianOrReadOnly,)

    def get_queryset(self):
        books = Book.objects.prefetch_related('authors').order_by('id')
        params = self.request.query_params
        if params.get('name'):
            books = books.filter(name__icontains=params['name'])
        if params.get('author', '').isdigit():
            books = books.filter(authors__id=params['author'])
        if params.get('year', '').isdigit():
            books = books.filter(year=params['year'])
        return books.distinct()


class AuthorViewSet(viewsets.ModelViewSet):
    """/api/v1/author/  and  /api/v1/author/{id}/  - CRUD for authors."""
    serializer_class = AuthorSerializer
    permission_classes = (IsLibrarianOrReadOnly,)
    queryset = Author.objects.prefetch_related('books').order_by('id')

    def destroy(self, request, *args, **kwargs):
        author = self.get_object()
        if author.books.exists():
            return Response({'detail': 'The author is attached to books and cannot be removed.'},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)
