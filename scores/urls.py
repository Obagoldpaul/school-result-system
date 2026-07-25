from django.urls import path
from . import views

urlpatterns = [
    path('', views.select_allocation, name='select_allocation'),
    path('enter/<int:allocation_id>/', views.enter_scores, name='enter_scores'),
]