from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_allocation, name='add_allocation'),
    path('', views.allocation_list, name='allocation_list'),
]