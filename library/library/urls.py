"""library URL Configuration"""
from django.contrib import admin
from django.urls import include, path

from authentication import views as auth_views

urlpatterns = [
    path('', auth_views.home, name='home'),
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('api-auth/', include('rest_framework.urls')),  # login link for the browsable API
    path('auth/', include('authentication.urls')),
    path('users/', include('authentication.users_urls')),
    path('books/', include('book.urls')),
    path('orders/', include('order.urls')),
    path('authors/', include('author.urls')),
]
