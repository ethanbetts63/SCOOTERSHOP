from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import get_user_model
from dashboard.models import SiteSettings

User = get_user_model()


def is_admin(user):
    return user.is_staff


def login_view(request):
    settings = SiteSettings.get_settings()
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not settings.enable_user_accounts and not (
                user.is_staff or user.is_superuser
            ):
                return render(
                    request,
                    "users/login.html",
                    {"message": "Login is currently restricted to administrators."},
                )

            login(request, user)
            next_url = request.GET.get("next", reverse("core:index"))
            return HttpResponseRedirect(next_url)
        else:
            return render(
                request,
                "users/login.html",
                {"message": "Invalid username and/or password."},
            )
    else:
        return render(request, "users/login.html")


def logout_view(request):
    if 'temp_service_booking_uuid' in request.session:
        del request.session['temp_service_booking_uuid']

    logout(request)
    return HttpResponseRedirect(reverse("core:index"))


def register(request):
    # Get the current site settings
    settings = SiteSettings.get_settings()

    # If user accounts are disabled, prevent registration
    if not settings.enable_user_accounts:
        return redirect("users:login")

    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(
                request, "users/register.html", {"message": "Passwords must match."}
            )
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(
                request, "users/register.html", {"message": "Username already taken."}
            )
        login(request, user)
        return HttpResponseRedirect(reverse("core:index"))
    else:
        return render(request, "users/register.html")
