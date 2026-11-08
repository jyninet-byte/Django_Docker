"""Access-control decorators shared by all apps."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def librarian_required(view):
    """Allow the view only for logged-in users with the librarian role."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_librarian:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


def visitor_required(view):
    """Allow the view only for logged-in users with the visitor (reader) role."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_librarian:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper
