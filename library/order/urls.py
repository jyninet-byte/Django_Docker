from django.urls import path

from . import views

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('my/', views.my_orders, name='my_orders'),
    path('create/', views.order_create, name='order_create'),
    path('<int:order_id>/edit/', views.order_edit, name='order_edit'),
    path('<int:order_id>/extend/', views.order_extend, name='order_extend'),
    path('<int:order_id>/close/', views.order_close, name='order_close'),
]
