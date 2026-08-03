from django.urls import path
from . import views

urlpatterns = [
    path('post/', views.post_announcement, name='post_announcement'),
    path('', views.announcement_list, name='announcement_list'),
]