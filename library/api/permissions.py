"""Permissions for the REST API.

* librarian (role = 1) or admin (is_staff) - full access to everything;
* reader (role = 0) - reads books and authors, sees only himself and only his own orders,
  can create an order for himself.
"""
from rest_framework import permissions


def is_librarian(user):
    return bool(user and user.is_authenticated and (user.role == 1 or user.is_staff))


class IsLibrarianOrReadOnly(permissions.BasePermission):
    """Books and authors: everyone logged in can read, only a librarian can change."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_librarian(request.user)


class UserPermission(permissions.BasePermission):
    """Users: a librarian can do everything, a reader can read and edit only himself."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if is_librarian(request.user):
            return True
        return request.method in ('GET', 'HEAD', 'OPTIONS', 'PUT', 'PATCH') and view.action != 'create'

    def has_object_permission(self, request, view, obj):
        return is_librarian(request.user) or obj == request.user


class OrderPermission(permissions.BasePermission):
    """Orders: a librarian can do everything, a reader can read his orders and create new ones."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if is_librarian(request.user):
            return True
        return request.method in permissions.SAFE_METHODS or request.method == 'POST'

    def has_object_permission(self, request, view, obj):
        return is_librarian(request.user) or obj.user == request.user
