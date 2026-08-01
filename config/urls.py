from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', include('dashboard.urls')),
    path('students/', include('students.urls')),
    path('teachers/', include('teachers.urls')),
    path('subjects/', include('subjects.urls')),
    path('allocations/', include('allocations.urls')),
    path('scores/', include('scores.urls')),
    path('billing/', include('billing.urls')),
]

from django.views.static import serve
from django.urls import re_path

urlpatterns += [
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]

if settings.DEBUG or True:  # local dev only
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

