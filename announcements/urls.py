from django.urls import path
from . import views


urlpatterns = [

    path(
        'post/',
        views.post_announcement,
        name='post_announcement'
    ),

    path(
        '<int:announcement_id>/',
        views.announcement_detail,
        name='announcement_detail'
    ),

    path(
        '<int:announcement_id>/pin/',
        views.toggle_announcement_pin,
        name='toggle_announcement_pin'
    ),

    path(
        '<int:announcement_id>/readers/',
        views.announcement_readers,
        name='announcement_readers'
    ),

    path(
        'delete/<int:announcement_id>/',
        views.delete_announcement,
        name='delete_announcement'
    ),

    path(
        '',
        views.announcement_list,
        name='announcement_list'
    ),
]