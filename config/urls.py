from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from accounts import views as account_views
from accounts.views import PlatformLoginView


urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        "login/",
        account_views.SchoolHubLoginView.as_view(),
        name="login",
    ),
    path(
        "platform/login/",
        PlatformLoginView.as_view(),
        name="platform_login",
    ),
    
    path(
        "set-password/<uidb64>/<token>/",
        account_views.SetPasswordView.as_view(),
        name="set_password",
    ),
    
    path(
        "password-reset/",
        account_views.PasswordResetRequestView.as_view(),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    path('', include('dashboard.urls')),
    path('academic/', include('academics.urls')),

    path('students/', include('students.urls')),
    path('teachers/', include('teachers.urls')),
    path('subjects/', include('subjects.urls')),
    path('allocations/', include('allocations.urls')),
    path('scores/', include('scores.urls')),
    path('billing/', include('billing.urls')),
    path('attendance/', include('attendance.urls')),
    path('announcements/', include('announcements.urls')),
    path("maintenance/", include("maintenance.urls")),
    
    path('platform/', include('schools.urls')),
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

