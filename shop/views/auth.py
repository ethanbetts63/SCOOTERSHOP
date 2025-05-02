# core/views/auth.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

# Handles user login
def login_view(request):
    if request.method == "POST":
        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            # Redirect to the page the user was trying to access, or index
            # Changed reverse("index") to reverse("shop:index")
            next_url = request.GET.get('next', reverse("shop:index"))
            return HttpResponseRedirect(next_url)
        else:
            return render(request, "accounts/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "accounts/login.html")

# Handles user logout
def logout_view(request):
    logout(request)
    # Changed reverse("index") to reverse("shop:index")
    return HttpResponseRedirect(reverse("shop:index"))

# Handles user registration
def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "accounts/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "accounts/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        # Changed reverse("index") to reverse("shop:index")
        return HttpResponseRedirect(reverse("shop:index"))
    else:
        return render(request, "accounts/register.html")