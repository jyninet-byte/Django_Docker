"""REST API, version 1.

Trailing slash is optional: /api/v1/book and /api/v1/book/ both work.
"""
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.trailing_slash = '/?'  # make the trailing slash optional
router.register(r'user/(?P<user_pk>\d+)/order', views.UserOrderViewSet, basename='user-order')
router.register(r'user', views.UserViewSet, basename='user')
router.register(r'order', views.OrderViewSet, basename='order')
router.register(r'book', views.BookViewSet, basename='book')
router.register(r'author', views.AuthorViewSet, basename='author')

urlpatterns = router.urls
