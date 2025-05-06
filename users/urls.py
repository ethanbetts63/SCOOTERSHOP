# SCOOTER_SHOP/users/urls.py

from django.urls import path
# You might use Django's built-in auth views or your own custom ones
# If using custom views from your old core/views/auth.py:
from .views import login_view, logout_view, register, admin_create_user_view
# If using Django's built-in views, you would import them differently:
# from django.contrib.auth import views as auth_views


app_name = 'users' # Set the app name for namespacing

urlpatterns = [
    # --- Authentication Views ---
    path("login/", login_view, name="login"), # Or auth_views.LoginView.as_view()
    path("logout/", logout_view, name="logout"), # Or auth_views.LogoutView.as_view()
    path("register/", register, name="register"),
    path("admin/create/", admin_create_user_view, name="admin_create_user"),


    # Add URLs for password reset etc. later if needed
]