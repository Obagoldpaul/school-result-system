from django.urls import path
from . import views

urlpatterns = [
    path('post/', views.post_announcement, name='post_announcement'),
    path('delete/<int:announcement_id>/', views.delete_announcement, name='delete_announcement'),
    path('', views.announcement_list, name='announcement_list'),
]