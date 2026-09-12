from django.urls import path
from . import views


urlpatterns = [
    path(
        "",
        views.platform_dashboard,
        name="platform_dashboard",
    ),
    
    path(
        "schools/",
        views.manage_schools,
        name="manage_schools",
    ),

    path(
        "schools/create/",
        views.create_school,
        name="create_school",
    ),
    
    path(
        "schools/<int:school_id>/",
        views.school_detail,
        name="school_detail",
    ),
    
    path(
        "schools/<int:school_id>/edit/",
        views.edit_school,
        name="edit_school",
    ),
    
    path(
        "platform/schools/<int:school_id>/users/create/",
        views.create_school_user,
        name="create_school_user",
    ),
    
    path(
        "platform/schools/<int:school_id>/users/<int:user_id>/edit/",
        views.edit_school_user,
        name="edit_school_user",
    ),
    
    path(
        "schools/<int:school_id>/users/",
        views.school_users,
        name="school_users",
    ),
    
    path(
        "schools/<int:school_id>/users/<int:user_id>/role/",
        views.assign_user_school_role,
        name="assign_user_school_role",
    ),
    
    path(
        "schools/<int:school_id>/users/<int:user_id>/send-setup-link/",
        views.send_user_setup_link,
        name="send_user_setup_link",
    ),
    
    path(
        "schools/<int:school_id>/subscription/edit/",
        views.edit_subscription,
        name="edit_subscription",
    ),
    
    path(
        "schools/<int:school_id>/status/",
        views.toggle_school_status,
        name="toggle_school_status",
    ),
    
    path(
        "settings/",
        views.platform_settings,
        name="platform_settings",
    ),
    
    path("packages/", views.manage_packages, name="manage_packages"),
    
    path("packages/create/", views.create_package, name="create_package"),
    
    path("packages/<int:package_id>/edit/", views.edit_package, name="edit_package"),
    
    path("packages/<int:package_id>/status/", views.toggle_package_status, name="toggle_package_status"),
    
    path(
        "features/",
        views.manage_features,
        name="manage_features",
    ),

    path(
        "features/create/",
        views.create_feature,
        name="create_feature",
    ),

    path(
        "features/<int:feature_id>/edit/",
        views.edit_feature,
        name="edit_feature",
    ),

    path(
        "features/<int:feature_id>/status/",
        views.toggle_feature_status,
        name="toggle_feature_status",
    ),
    
    path(
        "schools/<int:school_id>/roles/",
        views.manage_school_roles,
        name="manage_school_roles",
    ),

    path(
        "schools/<int:school_id>/roles/create/",
        views.create_school_role,
        name="create_school_role",
    ),
    
    path(
        "schools/<int:school_id>/roles/<int:role_id>/delete/",
        views.delete_school_role,
        name="delete_school_role",
    ),
    
    path(
        "schools/<int:school_id>/roles/<int:role_id>/edit/",
        views.edit_school_role,
        name="edit_school_role",
    ),
    
    path(
        "schools/<int:school_id>/roles/<int:role_id>/permissions/",
        views.manage_role_permissions,
        name="manage_role_permissions",
    ),

]