from django.urls import path

from . import views

urlpatterns = [
    path('', views.book_list, name='book_list'),
    path('new/', views.book_create, name='book_create'),
    path('<int:book_id>/', views.book_detail, name='book_detail'),
    path('<int:book_id>/edit/', views.book_edit, name='book_edit'),
    path('user/<int:user_id>/', views.user_books, name='user_books'),
]
