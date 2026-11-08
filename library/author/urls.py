from django.urls import path

from . import views

urlpatterns = [
    path('', views.author_list, name='author_list'),
    path('create/', views.author_create, name='author_create'),
    path('<int:author_id>/edit/', views.author_edit, name='author_edit'),
    path('<int:author_id>/delete/', views.author_delete, name='author_delete'),
]
