# SCOOTER_SHOP/users/urls.py

from django.urls import path
from .views import login_view, logout_view, register, admin_create_user_view

app_name = 'users' 

urlpatterns = [
    # --- Authentication Views ---
    path("login/", login_view, name="login"), # Or auth_views.LoginView.as_view()
    path("logout/", logout_view, name="logout"), # Or auth_views.LogoutView.as_view()
    path("register/", register, name="register"),
    path("admin/create/", admin_create_user_view, name="admin_create_user"),
]