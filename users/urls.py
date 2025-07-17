from django.urls import path
from .views import login_view, logout_view, register

app_name = "users"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("register/", register, name="register"),
]
